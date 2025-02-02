from pycalcmodel.core.output import ModelOutput, ModelOutputType
from pyradioconfig.calculator_model_framework.interfaces.iprofile import IProfile
from pyradioconfig.parts.sol.profiles.sw_profile_outputs_common import sw_profile_outputs_common_sol
from pyradioconfig.parts.common.profiles.ocelot_regs import build_modem_regs_ocelot
from pyradioconfig.parts.common.utils.units_multiplier import UnitsMultiplier
from pyradioconfig.parts.common.profiles.profile_common import buildCrcOutputs, buildFecOutputs, buildFrameOutputs, \
    buildWhiteOutputs


class Profile_Connect_OFDM_Sol(IProfile):

    def __init__(self):
        self._profileName = "Connect_OFDM"
        self._readable_name = "Connect OFDM Profile"
        self._category = ""
        self._description = "Profile used for Connect OFDM PHYs"
        self._default = False
        self._activation_logic = ""
        self._family = "sol"
        self._sw_profile_outputs_common = sw_profile_outputs_common_sol()

    def buildProfileModel(self, model):

        # Build profile object and append it to the model
        profile = self._makeProfile(model)

        # Build inputs
        self.build_required_profile_inputs(model, profile)
        self.build_optional_profile_inputs(model, profile)
        self.build_advanced_profile_inputs(model, profile)
        self.build_hidden_profile_inputs(model, profile)

        # Build outputs
        self.build_register_profile_outputs(model, profile)
        self.build_variable_profile_outputs(model, profile)
        self.build_info_profile_outputs(model, profile)

        self._sw_profile_outputs_common.buildStudioLogOutput(model, profile)

    def profile_calculate(self, model):
        model.vars.protocol_id.value_forced = model.vars.protocol_id.var_enum.Connect
        self._fixed_ofdm_vars(model)
        self._lookup_from_ofdm_bw_mode(model)

    def build_required_profile_inputs(self, model, profile):

        IProfile.make_required_input(profile, model.vars.base_frequency_hz, "operational_frequency",
                                     readable_name="Base Channel Frequency", value_limit_min=100000000,
                                     value_limit_max=2500000000, units_multiplier=UnitsMultiplier.MEGA)

        IProfile.make_required_input(profile, model.vars.channel_spacing_hz, "operational_frequency",
                                     readable_name="Channel Spacing", value_limit_min=0, value_limit_max=10000000,
                                     units_multiplier=UnitsMultiplier.KILO)

        IProfile.make_required_input(profile, model.vars.xtal_frequency_hz, "crystal",
                                     readable_name="Crystal Frequency", value_limit_min=38000000,
                                     value_limit_max=40000000, units_multiplier=UnitsMultiplier.MEGA)

        IProfile.make_required_input(profile, model.vars.ofdm_option, "ofdm", readable_name="OFDM Bandwidth Mode")

    def build_optional_profile_inputs(self, model, profile):
        # No optional inputs for this profile
        pass

    def build_advanced_profile_inputs(self, model, profile):
        self.make_linked_io(profile, model.vars.fpll_band, 'crystal', readable_name="RF Frequency Planning Band")

    def build_hidden_profile_inputs(self, model, profile):
        # Hidden inputs to allow for fixed frame length testing
        self.make_hidden_input(profile, model.vars.frame_length_type, 'frame_general',
                                   readable_name="Frame Length Algorithm")
        self.make_hidden_input(profile, model.vars.fixed_length_size, category='frame_fixed_length',
                                   readable_name="Fixed Payload Size", value_limit_min=0, value_limit_max=0x7fffffff)
        self.make_hidden_input(profile, model.vars.ofdm_interleaving_depth, "Advanced", readable_name="SUN OFDM Interleaving Option")
        self.make_hidden_input(profile, model.vars.ofdm_stf_length, "Advanced",
                               readable_name="OFDM STF length (1 unit = 120us)",
                               value_limit_min=4, value_limit_max=25)

    def build_register_profile_outputs(self, model, profile):
        build_modem_regs_ocelot(model, profile)
        buildFrameOutputs(model, profile)
        buildCrcOutputs(model, profile)
        buildWhiteOutputs(model, profile)
        buildFecOutputs(model, profile)

        profile.outputs.append(ModelOutput(model.vars.ofdm_symbol_rate, '', ModelOutputType.RAIL_CONFIG,
                                           readable_name='Number of symbols sent in 1 second'))

    def build_variable_profile_outputs(self, model, profile):
        self._sw_profile_outputs_common.build_rail_outputs(model, profile)
        self._sw_profile_outputs_common.build_ircal_outputs(model, profile)

    def build_info_profile_outputs(self, model, profile):
        self._sw_profile_outputs_common.build_info_outputs(model, profile)

    def _lookup_from_ofdm_bw_mode(self, model):
        #This function calculates some variables/registers based on the ofdm bw mode

        #Read the mode from the profile inputs (not yet written to model vars)
        ofdm_bw_mode = model.profile.inputs.ofdm_option.var_value

        if ofdm_bw_mode == model.vars.ofdm_option.var_enum.OPT1_OFDM_BW_1p2MHz:
            # OPT 1
            model.vars.bitrate.value_forced = 2400000
        elif ofdm_bw_mode == model.vars.ofdm_option.var_enum.OPT2_OFDM_BW_0p8MHz:
            # OPT 2
            model.vars.bitrate.value_forced = 1200000
        elif ofdm_bw_mode == model.vars.ofdm_option.var_enum.OPT3_OFDM_BW_0p4MHz:
            # OPT 3
            model.vars.bitrate.value_forced = 600000
        elif ofdm_bw_mode == model.vars.ofdm_option.var_enum.OPT4_OFDM_BW_0p2MHz:
            # OPT 4
            model.vars.bitrate.value_forced = 300000

        self._fixed_ofdm_agc(model)
        self._fixed_ofdm_vars(model)

    def _fixed_ofdm_vars(self, model):
        model.vars.fec_tx_enable.value_forced = model.vars.fec_tx_enable.var_enum.DISABLED

        # Set defaults for shaping and whitening (for OFDM)
        model.vars.shaping_filter.value_forced = model.vars.shaping_filter.var_enum.Gaussian
        model.vars.shaping_filter_param.value_forced = 2.0

        # OFDM modulation
        model.vars.modulation_type.value_forced = model.vars.modulation_type.var_enum.OFDM

        # Use fullrate ADC (needs further study, improves sensitivity esp for OPT4 PHY)
        model.vars.adc_rate_mode.value_forced = model.vars.adc_rate_mode.var_enum.FULLRATE

        # Tolerance
        model.vars.rx_xtal_error_ppm.value_forced = 0
        model.vars.tx_xtal_error_ppm.value_forced = 0
        model.vars.baudrate_tol_ppm.value_forced = 0
        model.vars.deviation_tol_ppm.value_forced = 0

        # Encoding and Whitening (unused)
        model.vars.diff_encoding_mode.value_forced = model.vars.diff_encoding_mode.var_enum.DISABLED
        model.vars.dsss_chipping_code.value_forced = 0
        model.vars.dsss_len.value_forced = 0
        model.vars.dsss_spreading_factor.value_forced = 0
        model.vars.symbol_encoding.value_forced = model.vars.symbol_encoding.var_enum.NRZ
        model.vars.manchester_mapping.value_forced = model.vars.manchester_mapping.var_enum.Default
        model.vars.frame_coding.value_forced = model.vars.frame_coding.var_enum.NONE
        model.vars.white_poly.value_forced = model.vars.white_poly.var_enum.NONE
        model.vars.white_seed.value_forced = 0
        model.vars.white_output_bit.value_forced = 0

        # Preamble and syncword (unused)
        model.vars.preamble_length.value_forced = 2
        model.vars.preamble_pattern.value_forced = 1
        model.vars.preamble_pattern_len.value_forced = 2
        model.vars.syncword_0.value_forced = 0x12345678
        model.vars.syncword_1.value_forced = 0x12345678
        model.vars.syncword_length.value_forced = 16

        # Modulation parameters (unused)
        model.vars.deviation.value_forced = 0
        model.vars.fsk_symbol_map.value_forced = model.vars.fsk_symbol_map.var_enum.MAP0

        # Frame settings (unused)
        model.vars.frame_bitendian.value_forced = model.vars.frame_bitendian.var_enum.LSB_FIRST
        model.vars.frame_length_type.value_forced = model.vars.frame_length_type.var_enum.FIXED_LENGTH
        model.vars.payload_white_en.value_forced = True
        model.vars.payload_crc_en.value_forced = False
        model.vars.header_en.value_forced = True
        model.vars.header_size.value_forced = 1
        model.vars.header_calc_crc.value_forced = False
        model.vars.header_white_en.value_forced = False
        model.vars.var_length_numbits.value_forced = 8
        model.vars.var_length_bitendian.value_forced = model.vars.var_length_bitendian.var_enum.LSB_FIRST
        model.vars.var_length_shift.value_forced = 0
        model.vars.var_length_minlength.value_forced = 5
        model.vars.var_length_maxlength.value_forced = 0x7F
        model.vars.var_length_includecrc.value_forced = False
        model.vars.var_length_adjust.value_forced = 0
        model.vars.var_length_byteendian.value_forced = model.vars.var_length_byteendian.var_enum.LSB_FIRST
        model.vars.crc_poly.value_forced = model.vars.crc_poly.var_enum.ANSIX366_1979
        model.vars.crc_seed.value_forced = 0x00000000
        model.vars.crc_input_order.value_forced = model.vars.crc_input_order.var_enum.LSB_FIRST
        model.vars.crc_bit_endian.value_forced = model.vars.crc_bit_endian.var_enum.MSB_FIRST
        model.vars.crc_byte_endian.value_forced = model.vars.crc_byte_endian.var_enum.MSB_FIRST
        model.vars.crc_pad_input.value_forced = False
        model.vars.crc_invert.value_forced = False
        model.vars.fixed_length_size.value_forced = 1
        model.vars.frame_type_0_filter.value_forced = True
        model.vars.frame_type_0_length.value_forced = 0
        model.vars.frame_type_0_valid.value_forced = False
        model.vars.frame_type_1_filter.value_forced = True
        model.vars.frame_type_1_length.value_forced = 0
        model.vars.frame_type_1_valid.value_forced = False
        model.vars.frame_type_2_filter.value_forced = True
        model.vars.frame_type_2_length.value_forced = 0
        model.vars.frame_type_2_valid.value_forced = False
        model.vars.frame_type_3_filter.value_forced = True
        model.vars.frame_type_3_length.value_forced = 0
        model.vars.frame_type_3_valid.value_forced = False
        model.vars.frame_type_4_filter.value_forced = True
        model.vars.frame_type_4_length.value_forced = 0
        model.vars.frame_type_4_valid.value_forced = False
        model.vars.frame_type_5_filter.value_forced = True
        model.vars.frame_type_5_length.value_forced = 0
        model.vars.frame_type_5_valid.value_forced = False
        model.vars.frame_type_6_filter.value_forced = True
        model.vars.frame_type_6_filter.value_forced = True
        model.vars.frame_type_6_length.value_forced = 0
        model.vars.frame_type_6_valid.value_forced = False
        model.vars.frame_type_7_filter.value_forced = True
        model.vars.frame_type_7_length.value_forced = 0
        model.vars.frame_type_7_valid.value_forced = False
        model.vars.frame_type_bits.value_forced = 3
        model.vars.frame_type_loc.value_forced = 0
        model.vars.frame_type_lsbit.value_forced = 0

        # Other
        model.vars.asynchronous_rx_enable.value_forced = False
        model.vars.syncword_tx_skip.value_forced = False

    def _fixed_ofdm_agc(self, model):
        ofdm_bw_mode = model.profile.inputs.ofdm_option.var_value

        # AGC - from Wisun OFDM
        model.vars.RAC_LNAMIXTRIM4_LNAMIXRFPKDTHRESHSELHI.value_forced = 5  # 60mVrms
        model.vars.RAC_PGACTRL_PGATHRPKDHISEL.value_forced = 3  # 125mV
        model.vars.RAC_PGACTRL_PGATHRPKDLOSEL.value_forced = 0  # 100mV
        model.vars.AGC_GAINSTEPLIM1_PNINDEXMAX.value_forced = 17  # Per Yang Gao 10/1/20
        model.vars.AGC_GAINRANGE_PNGAINSTEP.value_forced = 3
        model.vars.AGC_AGCPERIOD0_PERIODHI.value_forced = 44
        model.vars.AGC_HICNTREGION0_HICNTREGION0.value_forced = 37  # PERIODHI-SETTLETIMEIF-1
        model.vars.AGC_HICNTREGION0_HICNTREGION1.value_forced = 100
        model.vars.AGC_HICNTREGION0_HICNTREGION2.value_forced = 100
        model.vars.AGC_HICNTREGION0_HICNTREGION3.value_forced = 100
        model.vars.AGC_HICNTREGION1_HICNTREGION4.value_forced = 100
        model.vars.AGC_AGCPERIOD0_MAXHICNTTHD.value_forced = 100  # > PERIODHI means disabled
        model.vars.AGC_STEPDWN_STEPDWN0.value_forced = 1
        model.vars.AGC_STEPDWN_STEPDWN1.value_forced = 2
        model.vars.AGC_STEPDWN_STEPDWN2.value_forced = 2
        model.vars.AGC_STEPDWN_STEPDWN3.value_forced = 2
        model.vars.AGC_STEPDWN_STEPDWN4.value_forced = 2
        model.vars.AGC_STEPDWN_STEPDWN5.value_forced = 2
        model.vars.AGC_CTRL7_SUBDEN.value_forced = 1
        model.vars.AGC_CTRL7_SUBINT.value_forced = 16
        model.vars.AGC_CTRL7_SUBNUM.value_forced = 0
        model.vars.AGC_CTRL7_SUBPERIOD.value_forced = 1

        if ofdm_bw_mode == model.vars.ofdm_option.var_enum.OPT1_OFDM_BW_1p2MHz:
            model.vars.AGC_CTRL4_RFPKDPRDGEAR.value_forced = 2  # 25usec dispngainup period
            model.vars.AGC_AGCPERIOD1_PERIODLOW.value_forced = 960  # 960 STF cycle = 24 usec
            model.vars.AGC_CTRL1_RSSIPERIOD.value_forced = 3
            model.vars.AGC_CTRL1_PWRPERIOD.value_forced = 2
        elif ofdm_bw_mode == model.vars.ofdm_option.var_enum.OPT2_OFDM_BW_0p8MHz:
            model.vars.AGC_CTRL4_RFPKDPRDGEAR.value_forced = 2  # 25usec dispngainup period
            model.vars.AGC_AGCPERIOD1_PERIODLOW.value_forced = 1920  # STF cycle = 48 usec
            model.vars.AGC_CTRL1_RSSIPERIOD.value_forced = 3
            model.vars.AGC_CTRL1_PWRPERIOD.value_forced = 2
        elif ofdm_bw_mode == model.vars.ofdm_option.var_enum.OPT3_OFDM_BW_0p4MHz:
            model.vars.AGC_CTRL4_RFPKDPRDGEAR.value_forced = 2  # 25usec dispngainup period
            model.vars.AGC_AGCPERIOD1_PERIODLOW.value_forced = 3840  # STF cycle = 96 usec
            model.vars.AGC_CTRL1_RSSIPERIOD.value_forced = 2
            model.vars.AGC_CTRL1_PWRPERIOD.value_forced = 1
        else:
            model.vars.AGC_CTRL4_RFPKDPRDGEAR.value_forced = 1  # 48usec dispngainup period
            model.vars.AGC_AGCPERIOD1_PERIODLOW.value_forced = 3840  # STF cycle = 96 usec
            model.vars.AGC_CTRL1_RSSIPERIOD.value_forced = 2
            model.vars.AGC_CTRL1_PWRPERIOD.value_forced = 2

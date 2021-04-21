PLOT_COLOR = 'k'
PLOT_COLOR_HIGHLIGHT = '#ff0000'
PLOT_ALPHA = .3
PLOT_ALPHA_HIGHLIGHT = 1
PLOT_WIDTH = 1.5
PLOT_WIDTH_HIGHLIGHT = 2

ROI_COLOR_SELECTED = '#00aa00'
ROI_COLOR_DESELECTED = '#0088ff'
ROI_COLOR_UNTRACKABLE = '#cc00cc'
ROI_COLOR_HIGHLIGHT = '#ff0000'
ROI_WIDTH = 1
ROI_WIDTH_HIGHLIGHT = 3

DESELECTED_DARKEN_FACTOR = .3


CMD_INIT_SESSION = 'cmd_init_session'
CMD_READ_SESSION_FROM_DISK = 'cmd_read_session_from_disk'
CMD_SAVE_SESSION_TO_DISK = 'cmd_save_session_to_disk'
CMD_CONFIG_SESSION = 'cmd_config_session'
CMD_SET_MICROSCOPE = 'cmd_set_microscope'
CMD_SET_SESSION = 'cmd_set_session'
CMD_DISCARD_SESSION = 'cmd_discard_session'
CMD_NEW_STACK = 'cmd_new_stack'
CMD_UPDATE_STACK_LIST = 'cmd_update_stack_list'
CMD_CLOSE_STACK = 'cmd_close_stack'
CMD_UPDATE_TRACES = 'cmd_update_traces'
CMD_TOOL_BINARIZE = 'cmd_tool_binarize'
CMD_TOOL_BGCORR = 'cmd_tool_bgcorr'

RESP_NEW_SESSION_ID = 'resp_new_session_id'

# ChannelCollection
#EVT_CLOSE = 'ChannelCollection_close' #TODO: delete
EVT_STACK_ADDED = 'ChannelCollection_stack-added'
EVT_STACK_RENAMED = 'ChannelCollection_stack-renamed'
EVT_STACK_DROPPED = 'ChannelCollection_stack-dropped'
EVT_CHANNELS_REORDERED = 'ChannelCollection_channels-reordered'
EVT_CHANNEL_SPEC_CHANGE = 'ChannelCollection_channel-spec-change'

CH_CAT_PHC = 'Phase-contrast'
CH_CAT_FL = 'Fluorescence'
CH_CAT_BIN = 'Binary'
CH_CAT_LBL = 'Label'
CH_CAT_LIST = (CH_CAT_PHC, CH_CAT_FL, CH_CAT_BIN, CH_CAT_LBL)

DT_CAT_AREA = 'Area'
#TYPE_AREA = DT_CAT_AREA #TODO: Remove `TYPE_AREA`
DT_CAT_FL = 'Fluorescence'
DT_CAT_LIST = (DT_CAT_AREA, DT_CAT_FL)

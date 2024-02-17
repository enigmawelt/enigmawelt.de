# enigmawelt.de
Enigmawelt - The biggest DreamOS/Enigma2 Video Blog

Open Alliance Plugin Enigmawelt

The plugin allows easy access to all previously published videos from VideoBlog 'Enigmawelt'. The functions are limited to the known RCU buttons.

- Horizontal directional pad (page-by-page scrolling)
- Vertical directional pad (select entry from the list)
- OK Play videos of the selected list entry
- EXIT Ends the playback of a video and or exits the plugin

Manual installation:

- create a directory on the box ... /usr/lib/enigma2/python/Plugins/Extensions/Enigmawelt
- copy the content of /src into this directory
- restart Enigma2

v1.1
- Search function added
- Return from the search results list, call up the search again and confirm the empty search with green

v1.1.1
- Fix AttributeError: 'NoneType' object has no attribute 'startswith'
- Fix [Skin] Error: Font 'Verdana' (in 'Verdana;35') is not defined! Using 'Body' font ('screen_text') instead.
- small code cleanup
- fix TypeError: 'NoneType' object is not subscriptable

v1.2

- add download function
- fix HTML entity character
- search if no entry message "no entry"
- yellow again cancels the filter
- button graphic size reduced & blue added
- code cleanup
- add postrm in

v1.2.1
- Skin changes to vertical color buttons and matrix style for OK and EXIT

v1.3
- add FHD and HD Skin
- Download Function
- add Option Menu Download Path, Description, Cover, Playback Position
- add new Skin Elements
- add new Button Functions
- reconfigure Skins

v1.3.1
- Add Version Number Head

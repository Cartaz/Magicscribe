pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Window

ApplicationWindow {
    id: root
    objectName: "controlPanel"

    required property var drawingAdapter
    required property var toolAdapter
    required property var shellAdapter
    required property var toolModel

    readonly property var colorPresets: [
        "#ff0000", "#ff8800", "#ffcc00", "#27ae60",
        "#00bfa5", "#e040fb", "#ffffff", "#6b7076"
    ]
    readonly property real preferredHeight: 700
    readonly property real currentScreenHeight: Screen.height > 0
                                                ? Screen.height
                                                : preferredHeight + 40
    readonly property real desktopAvailableHeight: Screen.desktopAvailableHeight > 0
                                                    ? Screen.desktopAvailableHeight
                                                    : currentScreenHeight
    readonly property real safeDesktopHeight: Math.min(
                                                  currentScreenHeight,
                                                  desktopAvailableHeight
                                              )

    visible: false
    width: 104
    height: Math.max(160, Math.min(preferredHeight, safeDesktopHeight - 40))
    minimumWidth: 104
    minimumHeight: Math.min(360, Math.max(160, safeDesktopHeight - 40))
    maximumWidth: 104
    maximumHeight: preferredHeight
    title: "MagicScribe"
    color: "transparent"
    flags: Qt.FramelessWindowHint
           | Qt.WindowStaysOnTopHint
           | Qt.Tool

    onClosing: function(close) {
        close.accepted = false
        root.shellAdapter.quit_application()
    }

    Shortcut {
        sequence: root.shellAdapter.toggleDrawingShortcut
        context: Qt.WindowShortcut
        enabled: !root.shellAdapter.globalDrawingShortcutsActive
        onActivated: root.drawingAdapter.toggle_drawing()
    }
    Shortcut {
        sequence: root.shellAdapter.visibilityShortcut
        context: Qt.WindowShortcut
        enabled: !root.shellAdapter.globalDrawingShortcutsActive
        onActivated: root.drawingAdapter.toggle_visibility()
    }
    Shortcut {
        sequence: root.shellAdapter.clearShortcut
        context: Qt.WindowShortcut
        enabled: !root.shellAdapter.globalDrawingShortcutsActive
        onActivated: root.drawingAdapter.clear_screen()
    }
    Shortcut {
        sequence: root.shellAdapter.undoShortcut
        context: Qt.WindowShortcut
        enabled: !root.shellAdapter.globalDrawingShortcutsActive
        onActivated: root.drawingAdapter.undo()
    }
    Shortcut {
        sequence: root.shellAdapter.redoShortcut
        context: Qt.WindowShortcut
        enabled: !root.shellAdapter.globalDrawingShortcutsActive
        onActivated: root.drawingAdapter.redo()
    }
    Shortcut {
        sequence: root.shellAdapter.minimizeShortcut
        context: Qt.WindowShortcut
        onActivated: root.shellAdapter.minimize_to_floating()
    }
    Shortcut {
        sequence: root.shellAdapter.quitShortcut
        context: Qt.WindowShortcut
        onActivated: root.shellAdapter.quit_application()
    }

    // Deliberately flat outer shell: desktop-floating chrome must not cast
    // highlight/shadow halos onto whatever is underneath it.
    Rectangle {
        id: toolbarSurface
        anchors.fill: parent
        anchors.margins: 12
        radius: Theme.radiusXL
        color: Theme.surface

        Flickable {
            id: toolbarViewport
            anchors.fill: parent
            anchors.margins: 4
            contentWidth: width
            contentHeight: toolbarColumn.implicitHeight + 20
            clip: contentHeight > height
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick

            ScrollBar.vertical: ScrollBar {
                policy: toolbarViewport.contentHeight > toolbarViewport.height
                        ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            }

            Column {
                id: toolbarColumn
                x: (toolbarViewport.width - width) / 2
                y: 10
                width: 64
                spacing: 5

                Button {
                    id: logoButton
                    objectName: "minimizeButton"
                    width: 48
                    height: 48
                    anchors.horizontalCenter: parent.horizontalCenter
                    hoverEnabled: true
                    focusPolicy: Qt.StrongFocus
                    padding: 0
                    Accessible.name: "Riduci MagicScribe"

                    background: RaisedSurface {
                        radius: 24

                        Rectangle {
                            anchors.fill: parent
                            radius: 24
                            color: "transparent"
                            border.width: logoButton.activeFocus || logoButton.pressed ? 1 : 0
                            border.color: Theme.accent
                        }
                    }

                    contentItem: Image {
                        source: "../../../assets/icons/png/magicscribe_48.png"
                        sourceSize.width: 30
                        sourceSize.height: 30
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }

                    onClicked: root.shellAdapter.minimize_to_floating()

                    ToolTip.visible: hovered
                    ToolTip.delay: 350
                    ToolTip.text: "Riduci · " + root.shellAdapter.minimizeShortcut

                    DragHandler {
                        target: null
                        acceptedButtons: Qt.LeftButton
                        onActiveChanged: {
                            if (active)
                                root.startSystemMove()
                        }
                    }
                }

                Button {
                    id: drawingToggle
                    objectName: "drawingToggle"
                    width: 36
                    height: 24
                    anchors.horizontalCenter: parent.horizontalCenter
                    hoverEnabled: true
                    focusPolicy: Qt.StrongFocus
                    padding: 0
                    Accessible.name: root.drawingAdapter.active
                                     ? "Disattiva disegno"
                                     : "Attiva disegno"

                    background: InsetSurface {
                        radius: 12
                        focused: drawingToggle.activeFocus
                    }

                    contentItem: StatusIndicator {
                        active: root.drawingAdapter.active
                        anchors.centerIn: parent
                    }

                    onClicked: root.drawingAdapter.toggle_drawing()

                    ToolTip.visible: hovered
                    ToolTip.delay: 350
                    ToolTip.text: (root.drawingAdapter.active
                                   ? "Disegno attivo · disattiva"
                                   : "Disegno disattivato · attiva")
                                  + " · " + root.shellAdapter.toggleDrawingShortcut
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Qt.rgba(1.0, 1.0, 1.0, 0.07)
                }

                Column {
                    width: parent.width
                    spacing: 4

                    Repeater {
                        model: root.toolModel

                        delegate: NeuIconButton {
                            required property string toolId
                            required property string displayLabel
                            required property string glyph
                            required property bool supportsColor

                            width: 44
                            height: 44
                            anchors.horizontalCenter: parent.horizontalCenter
                            iconSource: "../../../assets/icons/toolbar/" + toolId + ".svg"
                            toolTip: displayLabel
                            selected: root.toolAdapter.currentTool === toolId
                            onClicked: root.toolAdapter.select_tool(toolId)
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Qt.rgba(1.0, 1.0, 1.0, 0.07)
                }

                Column {
                    width: parent.width
                    spacing: 4

                    NeuIconButton {
                        width: 44
                        height: 44
                        anchors.horizontalCenter: parent.horizontalCenter
                        iconSource: "../../../assets/icons/toolbar/eye.svg"
                        toolTip: (root.drawingAdapter.annotationsVisible
                                  ? "Nascondi annotazioni"
                                  : "Mostra annotazioni")
                                 + " · " + root.shellAdapter.visibilityShortcut
                        selected: !root.drawingAdapter.annotationsVisible
                        onClicked: root.drawingAdapter.toggle_visibility()
                    }

                    NeuIconButton {
                        width: 44
                        height: 44
                        anchors.horizontalCenter: parent.horizontalCenter
                        iconSource: "../../../assets/icons/toolbar/undo.svg"
                        toolTip: "Annulla · " + root.shellAdapter.undoShortcut
                        enabled: root.drawingAdapter.canUndo
                        onClicked: root.drawingAdapter.undo()
                    }

                    NeuIconButton {
                        width: 44
                        height: 44
                        anchors.horizontalCenter: parent.horizontalCenter
                        iconSource: "../../../assets/icons/toolbar/redo.svg"
                        toolTip: "Ripristina · " + root.shellAdapter.redoShortcut
                        enabled: root.drawingAdapter.canRedo
                        onClicked: root.drawingAdapter.redo()
                    }

                    NeuIconButton {
                        width: 44
                        height: 44
                        anchors.horizontalCenter: parent.horizontalCenter
                        iconSource: "../../../assets/icons/toolbar/trash.svg"
                        toolTip: "Cancella schermo · " + root.shellAdapter.clearShortcut
                        onClicked: root.drawingAdapter.clear_screen()
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Qt.rgba(1.0, 1.0, 1.0, 0.07)
                }

                Item {
                    width: parent.width
                    height: 42

                    Text {
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "SIZE"
                        color: Theme.textDim
                        font.family: Theme.fontFamily
                        font.pixelSize: 8
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.8
                    }

                    Slider {
                        id: sizeSlider
                        anchors {
                            left: parent.left
                            right: parent.right
                            bottom: parent.bottom
                        }
                        height: 26
                        from: 1
                        to: 100
                        stepSize: 1
                        value: root.toolAdapter.currentSize
                        hoverEnabled: true
                        focusPolicy: Qt.StrongFocus

                        onPressedChanged: {
                            if (!pressed)
                                root.toolAdapter.set_size(Math.round(value))
                        }

                        background: InsetSurface {
                            x: sizeSlider.leftPadding
                            y: sizeSlider.topPadding
                               + sizeSlider.availableHeight / 2 - height / 2
                            width: sizeSlider.availableWidth
                            height: 6
                            radius: 3
                            focused: sizeSlider.activeFocus
                        }

                        handle: Rectangle {
                            x: sizeSlider.leftPadding
                               + sizeSlider.visualPosition
                               * (sizeSlider.availableWidth - width)
                            y: sizeSlider.topPadding
                               + sizeSlider.availableHeight / 2 - height / 2
                            width: 14
                            height: 14
                            radius: 7
                            color: Theme.surface
                            border.width: 2
                            border.color: Theme.accent
                        }

                        ToolTip.visible: hovered
                        ToolTip.delay: 350
                        ToolTip.text: "Dimensione: " + Math.round(value)
                    }
                }

                Grid {
                    width: 60
                    height: 32
                    anchors.horizontalCenter: parent.horizontalCenter
                    columns: 4
                    spacing: 4
                    opacity: root.toolAdapter.colorAvailable ? 1.0 : 0.28

                    Repeater {
                        model: root.colorPresets

                        delegate: Button {
                            id: swatch
                            required property string modelData

                            width: 12
                            height: 12
                            padding: 0
                            hoverEnabled: true
                            focusPolicy: Qt.StrongFocus
                            enabled: root.toolAdapter.colorAvailable
                            Accessible.name: "Colore " + modelData

                            onClicked: root.toolAdapter.set_color(modelData)

                            background: Rectangle {
                                radius: 6
                                color: swatch.modelData
                                border.width: root.toolAdapter.currentColor.toLowerCase()
                                              === swatch.modelData.toLowerCase()
                                              || swatch.activeFocus ? 2 : 1
                                border.color: root.toolAdapter.currentColor.toLowerCase()
                                              === swatch.modelData.toLowerCase()
                                              ? Theme.accent : Theme.textDim
                            }

                            ToolTip.visible: hovered
                            ToolTip.delay: 350
                            ToolTip.text: modelData
                        }
                    }
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    objectName: "controlPanel"

    required property QtObject drawingAdapter
    required property QtObject toolAdapter
    required property QtObject shellAdapter
    required property var toolModel

    readonly property var colorPresets: [
        "#ff0000", "#ff8800", "#ffcc00", "#27ae60",
        "#00bfa5", "#e040fb", "#ffffff", "#6b7076"
    ]

    visible: false
    width: 370
    height: 690
    minimumWidth: 340
    minimumHeight: 520
    maximumWidth: 440
    title: "MagicScribe"
    color: Theme.surface
    flags: Qt.Window | Qt.WindowStaysOnTopHint

    onClosing: function(close) {
        close.accepted = false
        root.shellAdapter.quitApplication()
    }

    Shortcut {
        sequence: root.shellAdapter.toggleDrawingShortcut
        context: Qt.WindowShortcut
        onActivated: root.drawingAdapter.toggleDrawing()
    }
    Shortcut {
        sequence: root.shellAdapter.visibilityShortcut
        context: Qt.WindowShortcut
        onActivated: root.drawingAdapter.toggleVisibility()
    }
    Shortcut {
        sequence: root.shellAdapter.clearShortcut
        context: Qt.WindowShortcut
        onActivated: root.drawingAdapter.clearScreen()
    }
    Shortcut {
        sequence: root.shellAdapter.undoShortcut
        context: Qt.WindowShortcut
        onActivated: root.drawingAdapter.undo()
    }
    Shortcut {
        sequence: root.shellAdapter.redoShortcut
        context: Qt.WindowShortcut
        onActivated: root.drawingAdapter.redo()
    }
    Shortcut {
        sequence: root.shellAdapter.minimizeShortcut
        context: Qt.WindowShortcut
        onActivated: root.shellAdapter.minimizeToFloating()
    }
    Shortcut {
        sequence: root.shellAdapter.quitShortcut
        context: Qt.WindowShortcut
        onActivated: root.shellAdapter.quitApplication()
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: scroll.availableWidth
            spacing: 14

            Item { Layout.preferredHeight: 4 }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                spacing: 12

                Image {
                    source: "../../../assets/icons/png/magicscribe_48.png"
                    sourceSize.width: 40
                    sourceSize.height: 40
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    fillMode: Image.PreserveAspectFit
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Text {
                        text: "MagicScribe"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: "Annotazioni sullo schermo"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                    }
                }

                StatusIndicator {
                    active: root.drawingAdapter.active
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 22
                Layout.rightMargin: 22
                text: root.drawingAdapter.active ? "Disegno attivo" : "Disegno disattivato"
                color: root.drawingAdapter.active ? Theme.accent : Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: Font.Medium
            }

            RaisedSurface {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 184
                strong: true
                radius: Theme.radiusLarge

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 9

                    Text {
                        text: "DISEGNO"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.1
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        NeuButton {
                            Layout.fillWidth: true
                            text: root.drawingAdapter.active
                                  ? "Disegno ATTIVO — disattiva"
                                  : "Attiva disegno"
                            selected: root.drawingAdapter.active
                            onClicked: root.drawingAdapter.toggleDrawing()
                        }
                        ShortcutBadge { text: root.shellAdapter.toggleDrawingShortcut }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        NeuButton {
                            Layout.fillWidth: true
                            text: root.drawingAdapter.annotationsVisible
                                  ? "Nascondi annotazioni"
                                  : "Mostra annotazioni"
                            enabled: root.drawingAdapter.active
                            onClicked: root.drawingAdapter.toggleVisibility()
                        }
                        ShortcutBadge { text: root.shellAdapter.visibilityShortcut }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        NeuButton {
                            Layout.fillWidth: true
                            text: "Cancella schermo"
                            enabled: root.drawingAdapter.active
                            onClicked: root.drawingAdapter.clearScreen()
                        }
                        ShortcutBadge { text: root.shellAdapter.clearShortcut }
                    }
                }
            }

            RaisedSurface {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 132
                radius: Theme.radiusMedium

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 9

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "CRONOLOGIA"
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.1
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: root.drawingAdapter.strokeCount + " tratti"
                            color: Theme.textDim
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        NeuButton {
                            Layout.fillWidth: true
                            text: "Annulla tratto"
                            enabled: root.drawingAdapter.canUndo
                            onClicked: root.drawingAdapter.undo()
                        }
                        ShortcutBadge { text: root.shellAdapter.undoShortcut }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        NeuButton {
                            Layout.fillWidth: true
                            text: "Ripristina tratto"
                            enabled: root.drawingAdapter.canRedo
                            onClicked: root.drawingAdapter.redo()
                        }
                        ShortcutBadge { text: root.shellAdapter.redoShortcut }
                    }
                }
            }

            RaisedSurface {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: root.toolAdapter.colorAvailable ? 248 : 204
                radius: Theme.radiusLarge

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    Text {
                        text: "STRUMENTI"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.1
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: 7
                        rowSpacing: 7

                        Repeater {
                            model: root.toolModel
                            delegate: NeuButton {
                                required property string toolId
                                required property string displayLabel
                                required property string glyph
                                required property bool supportsColor

                                Layout.fillWidth: true
                                compact: true
                                text: glyph + "  " + displayLabel
                                selected: root.toolAdapter.currentTool === toolId
                                onClicked: root.toolAdapter.selectTool(toolId)
                            }
                        }
                    }

                    Text {
                        visible: root.toolAdapter.colorAvailable
                        text: "Colore"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                    }

                    RowLayout {
                        visible: root.toolAdapter.colorAvailable
                        Layout.fillWidth: true
                        spacing: 7

                        Repeater {
                            model: root.colorPresets
                            delegate: Button {
                                id: swatch
                                required property string modelData

                                implicitWidth: 28
                                implicitHeight: 28
                                hoverEnabled: true
                                focusPolicy: Qt.StrongFocus
                                onClicked: root.toolAdapter.setColor(modelData)

                                background: Rectangle {
                                    radius: 14
                                    color: swatch.modelData
                                    border.width: root.toolAdapter.currentColor.toLowerCase()
                                                  === swatch.modelData.toLowerCase() ? 2 : 1
                                    border.color: root.toolAdapter.currentColor.toLowerCase()
                                                  === swatch.modelData.toLowerCase()
                                                  ? Theme.accent : Theme.textDim
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: "Dimensione"
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                        }

                        Slider {
                            id: sizeSlider
                            Layout.fillWidth: true
                            from: 1
                            to: 100
                            stepSize: 1
                            value: root.toolAdapter.currentSize
                            focusPolicy: Qt.StrongFocus

                            onPressedChanged: {
                                if (!pressed)
                                    root.toolAdapter.setSize(Math.round(value))
                            }

                            background: InsetSurface {
                                x: sizeSlider.leftPadding
                                y: sizeSlider.topPadding
                                   + sizeSlider.availableHeight / 2 - height / 2
                                width: sizeSlider.availableWidth
                                height: 7
                                radius: 3.5
                                focused: sizeSlider.activeFocus
                            }

                            handle: Rectangle {
                                x: sizeSlider.leftPadding
                                   + sizeSlider.visualPosition
                                   * (sizeSlider.availableWidth - width)
                                y: sizeSlider.topPadding
                                   + sizeSlider.availableHeight / 2 - height / 2
                                width: 18
                                height: 18
                                radius: 9
                                color: Theme.surface
                                border.width: 2
                                border.color: Theme.accent
                            }
                        }

                        InsetSurface {
                            Layout.preferredWidth: 44
                            Layout.preferredHeight: 28
                            radius: 9

                            Text {
                                anchors.centerIn: parent
                                text: Math.round(sizeSlider.value)
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.bottomMargin: 18
                spacing: 10

                Text {
                    Layout.fillWidth: true
                    text: "Riduci il pannello per liberare l'area di lavoro"
                    color: Theme.textDim
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }

                NeuButton {
                    text: "Riduci"
                    compact: true
                    Layout.preferredWidth: 84
                    onClicked: root.shellAdapter.minimizeToFloating()
                }

                ShortcutBadge { text: root.shellAdapter.minimizeShortcut }
            }
        }
    }
}

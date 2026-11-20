pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window

Window {
    id: root
    objectName: "floatingPalette"

    required property var drawingAdapter
    required property var shellAdapter

    property alias layerShellPaletteX: paletteHost.x
    property alias layerShellPaletteY: paletteHost.y

    readonly property real paletteWidth: 58
    readonly property real paletteHeight: 58
    readonly property real currentScreenWidth: Screen.width > 0
                                               ? Screen.width
                                               : paletteWidth + 40
    readonly property real currentScreenHeight: Screen.height > 0
                                                ? Screen.height
                                                : paletteHeight + 40

    visible: false
    width: currentScreenWidth
    height: currentScreenHeight
    color: "transparent"
    title: "MagicScribe"
    flags: Qt.FramelessWindowHint
           | Qt.WindowStaysOnTopHint
           | Qt.Tool
           | Qt.WindowDoesNotAcceptFocus

    onVisibleChanged: {
        if (!root.visible)
            return
        // Collasso 1:1: il centro della palette ridotta coincide esattamente
        // con il centro del logo premuto nella toolbar. Al restore il verso
        // opposto sposta toolbarHost affinché il logo riappaia sul centro
        // corrente della floating icon.
        paletteHost.x = root.shellAdapter.controlLogoCenterX - paletteHost.width / 2
        paletteHost.y = root.shellAdapter.controlLogoCenterY - paletteHost.height / 2
        paletteHost.clampToSurface()
    }

    SurfaceHost {
        id: paletteHost
        objectName: "paletteHost"
        surface: root
        x: 20
        y: 20
        width: root.paletteWidth
        height: root.paletteHeight

        onInputRegionRequested: (regionX, regionY, regionWidth, regionHeight) => {
            root.shellAdapter.set_floating_input_region(
                        regionX, regionY, regionWidth, regionHeight)
        }

        RaisedSurface {
            id: paletteSurface
            anchors.centerIn: parent
            width: 40
            height: 40
            radius: 20

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: "transparent"
                border.width: root.drawingAdapter.active ? 1 : 0
                border.color: Theme.accent

                Behavior on border.width {
                    NumberAnimation { duration: Theme.animationFast }
                }
            }

            Image {
                anchors.centerIn: parent
                width: 22
                height: 22
                source: "../../../assets/icons/magicscribe.svg"
                sourceSize.width: 22
                sourceSize.height: 22
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            StatusIndicator {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.rightMargin: -4
                anchors.bottomMargin: -4
                width: 12
                height: 12
                active: root.drawingAdapter.active
            }
        }

        HoverHandler {
            cursorShape: Qt.PointingHandCursor
        }

        TapHandler {
            acceptedButtons: Qt.LeftButton
            onTapped: root.shellAdapter.restore_control_panel()
        }

        DragHandler {
            target: paletteHost
            acceptedButtons: Qt.LeftButton
            xAxis.minimum: 0
            xAxis.maximum: Math.max(0, root.width - paletteHost.width)
            yAxis.minimum: 0
            yAxis.maximum: Math.max(0, root.height - paletteHost.height)
        }
    }
}

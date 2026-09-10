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

    function syncLayerShellInputRegion() {
        if (!root.visible)
            return
        root.shellAdapter.set_floating_input_region(
                    paletteHost.x,
                    paletteHost.y,
                    paletteHost.width,
                    paletteHost.height)
    }

    function clampPaletteHost() {
        paletteHost.x = Math.max(
                    0,
                    Math.min(root.width - paletteHost.width, paletteHost.x))
        paletteHost.y = Math.max(
                    0,
                    Math.min(root.height - paletteHost.height, paletteHost.y))
    }

    onVisibleChanged: {
        if (root.visible) {
            // Collasso 1:1: il centro della palette ridotta coincide esattamente
            // con il centro del logo premuto nella toolbar. Al restore il verso
            // opposto sposta toolbarHost affinché il logo riappaia sul centro
            // corrente della floating icon.
            paletteHost.x = root.shellAdapter.controlLogoCenterX
                            - paletteHost.width / 2
            paletteHost.y = root.shellAdapter.controlLogoCenterY
                            - paletteHost.height / 2
        }
        clampPaletteHost()
        syncLayerShellInputRegion()
    }
    onWidthChanged: {
        clampPaletteHost()
        syncLayerShellInputRegion()
    }
    onHeightChanged: {
        clampPaletteHost()
        syncLayerShellInputRegion()
    }

    Item {
        id: paletteHost
        x: 20
        y: 20
        width: root.paletteWidth
        height: root.paletteHeight

        onXChanged: root.syncLayerShellInputRegion()
        onYChanged: root.syncLayerShellInputRegion()
        onWidthChanged: root.syncLayerShellInputRegion()
        onHeightChanged: root.syncLayerShellInputRegion()

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
                source: "../../../assets/icons/png/magicscribe_48.png"
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

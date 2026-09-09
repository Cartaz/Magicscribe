pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window

Window {
    id: root
    objectName: "floatingPalette"

    required property var drawingAdapter
    required property var shellAdapter

    property bool layerShellPlacement: false
    property real layerShellMarginLeft: 20
    property real layerShellMarginTop: 20

    visible: false
    width: 58
    height: 58
    color: "transparent"
    title: "MagicScribe"
    flags: Qt.FramelessWindowHint
           | Qt.WindowStaysOnTopHint
           | Qt.Tool
           | Qt.WindowDoesNotAcceptFocus

    function moveLayerShellBy(dx, dy) {
        if (!root.layerShellPlacement)
            return
        const maxLeft = Math.max(0, Screen.width - root.width)
        const maxTop = Math.max(0, Screen.height - root.height)
        root.layerShellMarginLeft = Math.max(
                    0, Math.min(maxLeft, root.layerShellMarginLeft + dx))
        root.layerShellMarginTop = Math.max(
                    0, Math.min(maxTop, root.layerShellMarginTop + dy))
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
        target: null
        acceptedButtons: Qt.LeftButton
        onActiveChanged: {
            if (active && !root.layerShellPlacement)
                root.startSystemMove()
        }
        xAxis.onActiveValueChanged: (delta) => {
            if (root.layerShellPlacement)
                root.moveLayerShellBy(delta, 0)
        }
        yAxis.onActiveValueChanged: (delta) => {
            if (root.layerShellPlacement)
                root.moveLayerShellBy(0, delta)
        }
    }
}

pragma ComponentBehavior: Bound

import QtQuick

Window {
    id: root
    objectName: "floatingPalette"

    required property var drawingAdapter
    required property var shellAdapter

    visible: false
    width: 80
    height: 80
    color: "transparent"
    title: "MagicScribe"
    flags: Qt.FramelessWindowHint
           | Qt.WindowStaysOnTopHint
           | Qt.Tool
           | Qt.WindowDoesNotAcceptFocus

    RaisedSurface {
        id: paletteSurface
        anchors.centerIn: parent
        width: 52
        height: 52
        radius: 26

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
            width: 28
            height: 28
            source: "../../../assets/icons/png/magicscribe_48.png"
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        StatusIndicator {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: -2
            anchors.bottomMargin: -2
            active: root.drawingAdapter.active
        }
    }

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: root.shellAdapter.restoreControlPanel()
    }

    DragHandler {
        target: null
        acceptedButtons: Qt.LeftButton
        onActiveChanged: {
            if (active)
                root.startSystemMove()
        }
    }
}

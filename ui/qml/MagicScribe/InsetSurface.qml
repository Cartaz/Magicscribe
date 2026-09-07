import QtQuick

Item {
    id: root

    property real radius: Theme.radiusSmall
    property color fillColor: Theme.surface
    property bool focused: false

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.fillColor
        border.width: root.focused ? 1 : 0
        border.color: Theme.accent
    }

    Rectangle {
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: 2
        }
        height: 2
        radius: 1
        color: Qt.rgba(0.0, 0.0, 0.0, 0.42)
    }

    Rectangle {
        anchors {
            left: parent.left
            top: parent.top
            bottom: parent.bottom
            margins: 2
        }
        width: 2
        radius: 1
        color: Qt.rgba(0.0, 0.0, 0.0, 0.36)
    }

    Rectangle {
        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            margins: 2
        }
        height: 1
        radius: 1
        color: Qt.rgba(1.0, 1.0, 1.0, 0.055)
    }

    Rectangle {
        anchors {
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            margins: 2
        }
        width: 1
        radius: 1
        color: Qt.rgba(1.0, 1.0, 1.0, 0.045)
    }
}

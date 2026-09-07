import QtQuick

Item {
    id: root

    property string text: ""

    implicitWidth: Math.max(54, label.implicitWidth + 16)
    implicitHeight: 24

    InsetSurface {
        anchors.fill: parent
        radius: 9
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: 10
        font.weight: Font.Medium
    }
}

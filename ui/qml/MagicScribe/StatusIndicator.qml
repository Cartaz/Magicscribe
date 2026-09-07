import QtQuick
import QtQuick.Effects

Item {
    id: root

    property bool active: false

    implicitWidth: 18
    implicitHeight: 18

    RectangularShadow {
        anchors.fill: dot
        offset: Qt.vector2d(0, 0)
        blur: 8
        spread: 1
        radius: 8
        color: Theme.accentGlow
        opacity: root.active ? dot.opacity : 0
        cached: false
    }

    Rectangle {
        id: dot
        anchors.centerIn: parent
        width: 10
        height: 10
        radius: 5
        color: root.active ? Theme.accent : Theme.textDim

        SequentialAnimation on opacity {
            running: root.active
            loops: Animation.Infinite
            NumberAnimation { from: 0.55; to: 1.0; duration: 750; easing.type: Easing.InOutSine }
            NumberAnimation { from: 1.0; to: 0.55; duration: 750; easing.type: Easing.InOutSine }
        }
    }
}

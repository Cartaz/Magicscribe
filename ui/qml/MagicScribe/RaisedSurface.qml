import QtQuick
import QtQuick.Effects

Item {
    id: root

    property real radius: Theme.radiusLarge
    property bool strong: false

    RectangularShadow {
        anchors.fill: surfaceRect
        z: -3
        offset: root.strong ? Qt.vector2d(8, 8) : Qt.vector2d(3.5, 3.5)
        blur: root.strong ? 20 : 10
        spread: 0
        radius: root.radius
        color: root.strong ? Theme.shadowDarkStrong : Theme.shadowDarkSoft
        cached: false
    }

    RectangularShadow {
        anchors.fill: surfaceRect
        z: -2
        offset: root.strong ? Qt.vector2d(-6, -6) : Qt.vector2d(-3, -3)
        blur: root.strong ? 15 : 8.5
        spread: 0
        radius: root.radius
        color: root.strong ? Theme.shadowLightStrong : Theme.shadowLightSoft
        cached: false
    }

    Rectangle {
        id: surfaceRect
        anchors.fill: parent
        z: -1
        radius: root.radius
        color: Theme.surface
    }
}

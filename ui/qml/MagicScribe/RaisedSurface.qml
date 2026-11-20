import QtQuick
import QtQuick.Effects

Item {
    id: root

    property real radius: Theme.radiusLarge

    RectangularShadow {
        anchors.fill: surfaceRect
        z: -3
        offset: Qt.vector2d(3.5, 3.5)
        blur: 10
        spread: 0
        radius: root.radius
        color: Theme.shadowDarkSoft
        cached: false
    }

    RectangularShadow {
        anchors.fill: surfaceRect
        z: -2
        offset: Qt.vector2d(-3, -3)
        blur: 8.5
        spread: 0
        radius: root.radius
        color: Theme.shadowLightSoft
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

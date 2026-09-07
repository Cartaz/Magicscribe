import QtQuick
import QtQuick.Controls
import QtQuick.Effects

Button {
    id: control

    property bool selected: false
    property bool compact: false

    implicitHeight: compact ? 36 : 42
    implicitWidth: 120
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    background: Item {
        RectangularShadow {
            anchors.fill: buttonSurface
            offset: control.hovered && !control.pressed
                    ? Qt.vector2d(4.5, 4.5)
                    : Qt.vector2d(3.5, 3.5)
            blur: control.hovered && !control.pressed ? 12 : 10
            radius: Theme.radiusSmall
            color: Theme.shadowDarkSoft
            opacity: control.pressed ? 0.35 : (control.enabled ? 1.0 : 0.35)
            cached: false
        }

        RectangularShadow {
            anchors.fill: buttonSurface
            offset: control.hovered && !control.pressed
                    ? Qt.vector2d(-3.8, -3.8)
                    : Qt.vector2d(-3, -3)
            blur: control.hovered && !control.pressed ? 10 : 8.5
            radius: Theme.radiusSmall
            color: Theme.shadowLightSoft
            opacity: control.pressed ? 0.25 : (control.enabled ? 1.0 : 0.3)
            cached: false
        }

        RectangularShadow {
            anchors.fill: buttonSurface
            offset: Qt.vector2d(0, 0)
            blur: 12
            spread: 0
            radius: Theme.radiusSmall
            color: Theme.accentGlow
            opacity: control.selected || control.activeFocus ? 1.0 : 0.0
            cached: false

            Behavior on opacity {
                NumberAnimation { duration: Theme.animationFast }
            }
        }

        Rectangle {
            id: buttonSurface
            anchors.fill: parent
            radius: Theme.radiusSmall
            color: Theme.surface
            border.width: control.activeFocus ? 1 : 0
            border.color: Theme.accent
            opacity: control.enabled ? 1.0 : 0.52
        }
    }

    contentItem: Text {
        text: control.text
        color: !control.enabled
               ? Theme.textDim
               : (control.selected ? Theme.accent : Theme.textPrimary)
        font.family: Theme.fontFamily
        font.pixelSize: control.compact ? 12 : 13
        font.weight: control.selected ? Font.DemiBold : Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}

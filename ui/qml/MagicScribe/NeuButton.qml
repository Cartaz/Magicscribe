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
            offset: control.hovered ? Qt.vector2d(4.5, 4.5) : Qt.vector2d(3.5, 3.5)
            blur: control.hovered ? 12 : 10
            radius: Theme.radiusSmall
            color: Theme.shadowDarkSoft
            opacity: control.selected ? 0.0 : (control.enabled ? 1.0 : 0.35)
            cached: false
        }
        RectangularShadow {
            anchors.fill: buttonSurface
            offset: control.hovered ? Qt.vector2d(-3.8, -3.8) : Qt.vector2d(-3, -3)
            blur: control.hovered ? 10 : 8.5
            radius: Theme.radiusSmall
            color: Theme.shadowLightSoft
            opacity: control.selected ? 0.0 : (control.enabled ? 1.0 : 0.3)
            cached: false
        }
        Rectangle {
            id: buttonSurface
            anchors.fill: parent
            radius: Theme.radiusSmall
            color: Theme.surface
            border.width: control.pressed || control.activeFocus ? 1 : 0
            border.color: Theme.accent
            opacity: control.enabled ? 1.0 : 0.52
        }
        InsetSurface {
            anchors.fill: parent
            visible: control.selected
            radius: Theme.radiusSmall
            fillColor: Theme.surface
            focused: control.activeFocus
        }
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusSmall
            color: "transparent"
            border.width: control.selected ? 1 : 0
            border.color: Theme.accent
            opacity: control.selected ? 0.45 : 0.0
        }
    }

    contentItem: Text {
        text: control.text
        color: !control.enabled ? Theme.textDim : (control.selected ? Theme.accent : Theme.textPrimary)
        opacity: control.pressed ? 0.72 : 1.0
        font.family: Theme.fontFamily
        font.pixelSize: control.compact ? 12 : 13
        font.weight: control.selected ? Font.DemiBold : Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}

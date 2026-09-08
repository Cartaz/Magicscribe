import QtQuick
import QtQuick.Controls
import QtQuick.Effects

Button {
    id: control

    property bool selected: false
    property url iconSource
    property string toolTip: ""

    implicitWidth: 44
    implicitHeight: 44
    padding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    Accessible.name: control.toolTip

    background: Item {
        RectangularShadow {
            anchors.fill: buttonSurface
            offset: control.hovered ? Qt.vector2d(4.5, 4.5) : Qt.vector2d(3.5, 3.5)
            blur: control.hovered ? 12 : 10
            radius: Theme.radiusSmall
            color: Theme.shadowDarkSoft
            opacity: control.selected ? 0.0 : (control.enabled ? 1.0 : 0.28)
            cached: false
        }

        RectangularShadow {
            anchors.fill: buttonSurface
            offset: control.hovered ? Qt.vector2d(-3.8, -3.8) : Qt.vector2d(-3, -3)
            blur: control.hovered ? 10 : 8.5
            radius: Theme.radiusSmall
            color: Theme.shadowLightSoft
            opacity: control.selected ? 0.0 : (control.enabled ? 1.0 : 0.24)
            cached: false
        }

        RectangularShadow {
            anchors.fill: buttonSurface
            offset: Qt.vector2d(0, 0)
            blur: 14
            radius: Theme.radiusSmall
            color: Theme.accentGlow
            opacity: control.selected && control.enabled ? 0.72 : 0.0
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
            opacity: control.enabled ? 1.0 : 0.48
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
            border.width: control.selected || control.pressed || control.activeFocus ? 1 : 0
            border.color: Theme.accent
            opacity: control.selected ? 0.58 : 1.0
        }
    }

    contentItem: Item {
        Image {
            anchors.centerIn: parent
            width: 22
            height: 22
            source: control.iconSource
            sourceSize.width: 22
            sourceSize.height: 22
            fillMode: Image.PreserveAspectFit
            smooth: true
            opacity: !control.enabled ? 0.34 : (control.pressed ? 0.62 : 0.92)
        }
    }

    ToolTip.visible: control.hovered
    ToolTip.delay: 350
    ToolTip.text: control.toolTip
}

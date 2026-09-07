pragma Singleton
import QtQuick

QtObject {
    readonly property color surface: "#141414"
    readonly property color accent: "#ff6600"
    readonly property color textPrimary: "#e1e1e1"
    readonly property color textSecondary: "#878787"
    readonly property color textDim: "#5a5a5a"

    readonly property color shadowDarkStrong: Qt.rgba(0.0, 0.0, 0.0, 0.62)
    readonly property color shadowLightStrong: Qt.rgba(1.0, 1.0, 1.0, 0.10)
    readonly property color shadowDarkSoft: Qt.rgba(0.0, 0.0, 0.0, 0.46)
    readonly property color shadowLightSoft: Qt.rgba(1.0, 1.0, 1.0, 0.075)
    readonly property color accentGlow: Qt.rgba(1.0, 0.4, 0.0, 0.28)

    readonly property string fontFamily: "Noto Sans"

    readonly property real radiusXL: 28
    readonly property real radiusLarge: 22
    readonly property real radiusMedium: 16
    readonly property real radiusSmall: 12

    readonly property int animationFast: 100
    readonly property int animationNormal: 160
}

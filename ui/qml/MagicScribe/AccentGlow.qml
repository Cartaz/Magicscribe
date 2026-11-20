import QtQuick
import QtQuick.Effects

// Alone arancione degli elementi evidenziati: strumento selezionato e logo
// della toolbar lo condividono, così il rendering resta identico.
RectangularShadow {
    property bool shown: true

    offset: Qt.vector2d(0, 0)
    blur: 14
    color: Theme.accentGlow
    opacity: shown ? 0.72 : 0.0
    cached: false

    Behavior on opacity {
        NumberAnimation { duration: Theme.animationFast }
    }
}

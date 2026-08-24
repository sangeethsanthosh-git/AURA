import QtQuick

Item {
    id: root
    property string stateName: "IDLE"
    property bool compact: false

    Rectangle {
        id: orb
        anchors.centerIn: parent
        width: compact ? 38 : 108
        height: width
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#efffff" }
            GradientStop { position: 0.35; color: root.stateName === "ERROR" ? "#ffd0d0" : "#b9fff2" }
            GradientStop { position: 0.70; color: root.stateName === "OBSERVING" ? "#9ed7ff" : "#77bef9" }
            GradientStop { position: 1.0; color: "#8059ff" }
        }
        border.color: "#ffffffaa"
        border.width: 1
        scale: root.stateName === "THINKING" || root.stateName === "LISTENING" ? 1.05 : 1.0

        Behavior on scale {
            NumberAnimation { duration: 520; easing.type: Easing.InOutQuad }
        }
    }

    SequentialAnimation on opacity {
        running: root.stateName === "THINKING" || root.stateName === "LISTENING"
        loops: Animation.Infinite
        NumberAnimation { to: 0.76; duration: 800; easing.type: Easing.InOutQuad }
        NumberAnimation { to: 1.0; duration: 800; easing.type: Easing.InOutQuad }
    }
}

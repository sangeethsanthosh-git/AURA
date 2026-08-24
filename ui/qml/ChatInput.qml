import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    signal send(string message)

    radius: 28
    color: Theme.surface
    border.color: Theme.border
    implicitHeight: 58

    RowLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        TextField {
            id: input
            Layout.fillWidth: true
            placeholderText: "Ask AURA anything..."
            color: Theme.textPrimary
            background: Rectangle { color: "transparent" }
            onAccepted: sendIfReady()
        }

        Button {
            text: auraBridge.voiceState === "LISTENING" ? "Stop" : "Mic"
            onClicked: auraBridge.voiceState === "LISTENING" ? auraBridge.stopListening() : auraBridge.startListening()
        }

        Button {
            text: "Send"
            enabled: input.text.trim().length > 0
            onClicked: sendIfReady()
        }
    }

    function sendIfReady() {
        var clean = input.text.trim()
        if (clean.length === 0)
            return
        root.send(clean)
        input.text = ""
    }
}

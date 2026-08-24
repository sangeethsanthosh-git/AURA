import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    color: "transparent"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 24
        anchors.rightMargin: 24
        spacing: 10

        Label {
            Layout.fillWidth: true
            text: "AURA is local-first"
            color: Theme.textMuted
            font.pixelSize: 13
        }

        StatusPill { label: "Backend"; value: auraBridge.backendState }
        StatusPill { label: "Mic"; value: auraBridge.voiceState }
        StatusPill { label: "Vision"; value: "On demand" }
    }
}

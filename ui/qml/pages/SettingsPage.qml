import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ScrollView {
    id: root
    contentWidth: availableWidth

    GridLayout {
        width: root.availableWidth
        columns: width < 900 ? 1 : 2
        columnSpacing: 16
        rowSpacing: 16
        anchors.margins: 28

        WidgetCard {
            Layout.fillWidth: true
            title: "System"
            Label { text: "Backend: " + auraBridge.backendState; color: Theme.textSecondary }
            Label { text: "Secrets are never exposed to QML."; color: Theme.textSecondary }
        }

        WidgetCard {
            Layout.fillWidth: true
            title: "Privacy"
            Label { text: "Microphone: " + auraBridge.voiceState; color: Theme.textSecondary }
            Label { text: "Vision: On demand"; color: Theme.textSecondary }
            Label { text: "Hands: routed through Python permissions"; color: Theme.textSecondary }
        }
    }
}

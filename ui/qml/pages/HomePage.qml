import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ScrollView {
    id: root
    required property var chatModel
    signal openChat()

    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 18
        anchors.margins: 28

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 190
            radius: Theme.radiusLarge
            color: Theme.surface
            border.color: Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.margins: 30
                spacing: 22

                AuraOrb {
                    Layout.preferredWidth: 112
                    Layout.preferredHeight: 112
                    stateName: auraBridge.appState
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Label {
                        text: "AURA"
                        color: Theme.accentStrong
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Label {
                        text: auraBridge.backendState === "READY" ? "I am here." : "Starting softly."
                        color: Theme.textPrimary
                        font.pixelSize: 42
                        font.bold: true
                    }
                    Label {
                        text: auraBridge.statusSummary
                        color: Theme.textSecondary
                        font.pixelSize: 14
                    }
                }

                Button {
                    text: auraBridge.backendState === "READY" ? "Open Chat" : "Retry"
                    onClicked: auraBridge.backendState === "READY" ? root.openChat() : auraBridge.retryBackend()
                }
            }
        }

        ChatInput {
            Layout.fillWidth: true
            onSend: function(message) {
                auraBridge.sendMessage(message)
                root.openChat()
            }
        }

        WidgetGrid {
            Layout.fillWidth: true
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    required property string currentPage
    signal navigate(string page)

    color: "#ffffff44"
    border.color: Theme.border

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            spacing: 12

            AuraOrb {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                stateName: auraBridge.appState
                compact: true
            }

            ColumnLayout {
                spacing: 1
                Label { text: "AURA"; font.pixelSize: 18; font.bold: true; color: Theme.textPrimary }
                Label { text: "ASUS V1"; font.pixelSize: 12; color: Theme.textSecondary }
            }
        }

        Repeater {
            model: ["Home", "Chat", "Tasks", "Knowledge", "Memory", "Activity", "Vision", "Voice", "Settings"]
            delegate: Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                text: modelData
                flat: true
                highlighted: root.currentPage === modelData
                onClicked: root.navigate(modelData)
                background: Rectangle {
                    radius: Theme.radiusSmall
                    color: highlighted || parent.hovered ? Theme.surface : "transparent"
                    border.color: highlighted ? Theme.border : "transparent"
                }
                contentItem: RowLayout {
                    spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 24
                        Layout.preferredHeight: 24
                        radius: 12
                        color: Theme.surfaceSecondary
                        Label {
                            anchors.centerIn: parent
                            text: modelData.substring(0, 1)
                            font.pixelSize: 11
                            color: Theme.textMuted
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: modelData
                        color: Theme.textPrimary
                        font.pixelSize: 14
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}

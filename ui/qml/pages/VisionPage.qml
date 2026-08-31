import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var status: ({})

    function refresh() {
        status = auraBridge.getVisionStatus()
    }

    Component.onCompleted: refresh()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 14

        WidgetCard {
            Layout.fillWidth: true
            title: "AURA EYES"

            ColumnLayout {
                spacing: 10

                Label {
                    text: "EYES " + (root.status.state || "OFF")
                    color: Theme.textPrimary
                    font.pixelSize: 22
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: [
                        "OCR: " + (root.status.ocr_available ? "Available" : "Unavailable"),
                        "Vision: " + (root.status.vision_available ? "Available" : "Unavailable"),
                        "Active window: " + (root.status.active_window_inspection ? "Available" : "Unavailable"),
                        "Continuous capture: " + (root.status.continuous_capture ? "On" : "Off"),
                        "OCR provider: " + (root.status.ocr_provider || "None"),
                        "Vision provider: " + (root.status.vision_provider || "None"),
                        "Languages: " + ((root.status.languages || []).join(", ") || "None"),
                        "Model policy: " + (root.status.model_policy || "UNLOAD_AFTER_TASK")
                    ].join("\n")
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                }

                RowLayout {
                    Button { text: "Look at Screen"; onClicked: auraBridge.sendMessage("Look at my screen.") }
                    Button { text: "Read Screen"; onClicked: auraBridge.sendMessage("Read my screen.") }
                    Button { text: "Describe Screen"; onClicked: auraBridge.sendMessage("What do you see on my screen?") }
                    Button { text: "Verify Screen"; onClicked: auraBridge.sendMessage("Verify the current screen state.") }
                    Button { text: "Refresh"; onClicked: root.refresh() }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}


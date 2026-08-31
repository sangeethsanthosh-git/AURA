import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "pages"

Item {
    id: root
    required property var chatModel
    property string currentPage: "Home"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.background }
            GradientStop { position: 1.0; color: Theme.backgroundSoft }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Sidebar {
            Layout.fillHeight: true
            Layout.preferredWidth: 208
            currentPage: root.currentPage
            onNavigate: function(page) { root.currentPage = page }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            TopBar {
                Layout.fillWidth: true
                Layout.preferredHeight: 62
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: ["Home", "Chat", "Tasks", "Knowledge", "Memory", "Activity", "Vision", "Voice", "Settings"].indexOf(root.currentPage)

                HomePage { chatModel: root.chatModel; onOpenChat: root.currentPage = "Chat" }
                ChatPage { chatModel: root.chatModel }
                CapabilityPage { title: "Tasks"; message: "No dedicated task store is exposed yet. Computer actions still work through chat." }
                CapabilityPage { title: "Knowledge"; message: "Use chat for RAG and document questions while a dedicated knowledge view is added." }
                MemoryPage {}
                ActivityPage {}
                VisionPage {}
                CapabilityPage { title: "Voice"; message: "Voice status is exposed. Push-to-talk controls will stay on demand." }
                SettingsPage {}
            }
        }
    }
}

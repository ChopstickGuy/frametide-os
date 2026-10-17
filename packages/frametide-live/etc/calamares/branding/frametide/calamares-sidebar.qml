/* Frametide OS – Seitenleiste des Installers
 * Erledigte Schritte: Häkchen · aktueller Schritt: Leuchtring + Akzentstreifen · kommende: gedimmt */
import io.calamares.ui 1.0
import io.calamares.core 1.0
import QtQuick 2.15
import QtQuick.Layouts 1.3

Rectangle {
    id: sideBar
    anchors.fill: parent
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#0F1428" }
        GradientStop { position: 1.0; color: "#05070F" }
    }

    readonly property color accent: "#22D3EE"
    readonly property color violet: "#A855F7"
    readonly property color textMain: "#F3F6FD"
    readonly property color textMuted: "#7D879C"

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 28
        anchors.bottomMargin: 20
        spacing: 0

        Image {
            Layout.alignment: Qt.AlignHCenter
            source: "file:/" + Branding.imagePath(Branding.ProductLogo)
            sourceSize.width: 64
            sourceSize.height: 64
            width: 64; height: 64
            fillMode: Image.PreserveAspectFit
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 10
            text: "Frametide OS"
            color: sideBar.textMain
            font.pixelSize: 17
            font.weight: Font.DemiBold
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 2
            Layout.bottomMargin: 26
            text: Branding.string(Branding.ShortVersionedName)
            color: sideBar.textMuted
            font.pixelSize: 12
        }

        Repeater {
            model: ViewManager
            delegate: Item {
                id: step
                readonly property bool current: index === ViewManager.currentStepIndex
                readonly property bool done: index < ViewManager.currentStepIndex
                Layout.fillWidth: true
                Layout.leftMargin: 14
                Layout.rightMargin: 14
                height: 42

                Rectangle {   // dezente Hervorhebung des aktuellen Schritts
                    anchors.fill: parent
                    radius: 10
                    color: step.current ? Qt.rgba(0.13, 0.83, 0.93, 0.12) : "transparent"
                    Behavior on color { ColorAnimation { duration: 180 } }
                }
                Rectangle {   // Akzentstreifen links
                    width: 3; radius: 2
                    height: parent.height - 16
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    color: sideBar.accent
                    visible: step.current
                }
                Rectangle {   // Kreis mit Nummer / Häkchen
                    id: dot
                    width: 22; height: 22; radius: 11
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    color: step.done ? sideBar.accent : "transparent"
                    border.width: step.done ? 0 : 2
                    border.color: step.current ? sideBar.accent : "#3A4256"
                    Text {
                        anchors.centerIn: parent
                        text: step.done ? "✓" : (index + 1)
                        color: step.done ? "#05070F" : (step.current ? sideBar.accent : sideBar.textMuted)
                        font.pixelSize: 11
                        font.weight: Font.Bold
                    }
                }
                Text {
                    anchors.left: dot.right
                    anchors.leftMargin: 12
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: display
                    elide: Text.ElideRight
                    color: step.current ? sideBar.textMain : (step.done ? "#B9C2D3" : sideBar.textMuted)
                    font.pixelSize: 14
                    font.weight: step.current ? Font.DemiBold : Font.Normal
                }
            }
        }

        Item { Layout.fillHeight: true }

        Rectangle {   // feine Verlaufslinie als Abschluss
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            height: 2
            radius: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: sideBar.accent }
                GradientStop { position: 1.0; color: sideBar.violet }
            }
            opacity: 0.6
        }
    }
}

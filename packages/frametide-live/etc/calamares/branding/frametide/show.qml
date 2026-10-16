import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation {
    id: presentation

    // Deutsch, sonst Englisch
    readonly property bool de: Qt.locale().name.startsWith("de")
    function nextSlide() { presentation.goToNextSlide(); }

    Timer {
        id: advanceTimer
        interval: 6000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    component FrametideSlide: Slide {
        property string heading
        property string body
        Rectangle { anchors.fill: parent; color: "#05070F" }
        Image {
            source: "logo.svg"; width: 96; height: 96
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 48
            sourceSize.width: 192; sourceSize.height: 192
        }
        Text {
            id: title
            text: heading; color: "#22D3EE"
            font.pixelSize: 28; font.weight: Font.DemiBold
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 172
        }
        Text {
            text: body; color: "#C9D1E3"; font.pixelSize: 16
            width: parent.width * 0.7; wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter; lineHeight: 1.3
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: title.bottom; anchors.topMargin: 20
        }
    }

    FrametideSlide {
        heading: presentation.de ? "Willkommen bei Frametide OS" : "Welcome to Frametide OS"
        body: presentation.de ? "Die Installation dauert nur wenige Minuten. Lehn dich zurück – wir kümmern uns um den Rest." : "Installation only takes a few minutes. Sit back – we'll take care of the rest."
    }
    FrametideSlide {
        heading: presentation.de ? "Treiber? Erledigt." : "Drivers? Done."
        body: presentation.de ? "Beim ersten Start erkennt Frametide deine Grafikkarte und richtet automatisch den besten Treiber ein – NVIDIA, AMD oder Intel." : "On first boot Frametide detects your graphics card and sets up the best driver automatically – NVIDIA, AMD or Intel."
    }
    FrametideSlide {
        heading: presentation.de ? "Bereit zum Spielen" : "Ready to play"
        body: presentation.de ? "Steam, Proton, GameMode und MangoHud sind schon an Bord. Einfach anmelden und loslegen." : "Steam, Proton, GameMode and MangoHud are already on board. Just sign in and play."
    }
    FrametideSlide {
        heading: presentation.de ? "Schnell und leise" : "Fast and quiet"
        body: presentation.de ? "Optimiert für kurze Startzeiten, niedrige Latenz und ein ruhiges, aufgeräumtes Design." : "Tuned for quick boot times, low latency and a calm, clean design."
    }

    function onActivate() { presentation.currentSlide = 0; }
    function onLeave() { }
}

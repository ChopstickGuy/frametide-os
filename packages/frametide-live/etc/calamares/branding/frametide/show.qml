import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation {
    id: presentation

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
        heading: "Willkommen bei Frametide OS"
        body: "Die Installation dauert nur wenige Minuten. Lehn dich zurück – wir kümmern uns um den Rest."
    }
    FrametideSlide {
        heading: "Treiber? Erledigt."
        body: "Beim ersten Start erkennt Frametide deine Grafikkarte und richtet automatisch den besten Treiber ein – NVIDIA, AMD oder Intel."
    }
    FrametideSlide {
        heading: "Bereit zum Spielen"
        body: "Steam, Proton, GameMode und MangoHud sind schon an Bord. Einfach anmelden und loslegen."
    }
    FrametideSlide {
        heading: "Schnell und leise"
        body: "Optimiert für kurze Startzeiten, niedrige Latenz und ein ruhiges, aufgeräumtes Design."
    }

    function onActivate() { presentation.currentSlide = 0; }
    function onLeave() { }
}

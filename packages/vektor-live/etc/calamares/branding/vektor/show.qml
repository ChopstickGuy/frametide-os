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

    component VektorSlide: Slide {
        property string heading
        property string body
        Rectangle { anchors.fill: parent; color: "#090C14" }
        Image {
            source: "logo.svg"; width: 96; height: 96
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 48
            sourceSize.width: 192; sourceSize.height: 192
        }
        Text {
            id: title
            text: heading; color: "#19E3D1"
            font.pixelSize: 28; font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 172
        }
        Text {
            text: body; color: "#E6EAF2"; font.pixelSize: 16
            width: parent.width * 0.7; wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter; lineHeight: 1.3
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: title.bottom; anchors.topMargin: 20
        }
    }

    VektorSlide {
        heading: "Willkommen bei Vektor OS"
        body: "Gebaut für maximale Gaming-Leistung, niedrige Latenz und ein klares, modernes Design."
    }
    VektorSlide {
        heading: "Treiber automatisch"
        body: "Beim ersten Start erkennt Vektor deine Grafikkarte und installiert den passenden Treiber – NVIDIA, AMD oder Intel, inklusive 32-Bit-Unterstützung für Steam."
    }
    VektorSlide {
        heading: "Bereit zum Spielen"
        body: "Steam, Proton, GameMode, MangoHud und Gamescope sind vorinstalliert. Tipp: Startoption „gamemoderun %command%“ in Steam."
    }
    VektorSlide {
        heading: "Schnell bis ins Detail"
        body: "zram, optimierte I/O-Scheduler, Low-Latency-Kernel-Einstellungen und VRR für ruckelfreie Bildraten."
    }

    function onActivate() { presentation.currentSlide = 0; }
    function onLeave() { }
}

import QtQuick
import QtQuick3D

Rectangle {
    color: "#061627"
    View3D {
        anchors.fill: parent
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Color
            clearColor: "#061627"
        }
        PerspectiveCamera {
            position: Qt.vector3d(0, 0, 410)
            clipFar: 1500
        }
        DirectionalLight {
            eulerRotation.x: -30
            eulerRotation.y: -25
            brightness: 3
            color: "#5BDFFF"
        }
        PointLight {
            position: Qt.vector3d(130, 80, 120)
            brightness: 22
            color: "#00D7FF"
        }
        Node {
            id: orbit
            NumberAnimation on eulerRotation.y {
                from: 0; to: 360
                duration: 9000
                loops: Animation.Infinite
            }
            NumberAnimation on eulerRotation.x {
                from: 8; to: 28
                duration: 4100
                loops: Animation.Infinite
                easing.type: Easing.InOutSine
            }
            Model {
                source: "#Sphere"
                scale: Qt.vector3d(1.15, 1.15, 1.15)
                materials: PrincipledMaterial {
                    baseColor: "#0B86BF"
                    roughness: 0.16
                    metalness: 0.65
                    emissiveFactor: Qt.vector3d(0.06, 0.28, 0.6)
                }
            }
            Model {
                source: "#Torus"
                scale: Qt.vector3d(1.65, 1.65, 1.65)
                eulerRotation.x: 65
                materials: PrincipledMaterial {
                    baseColor: "#55EFFF"
                    roughness: 0.20
                    metalness: 0.65
                    emissiveFactor: Qt.vector3d(0.3, 0.8, 1.0)
                }
            }
        }
    }
    Text {
        text: "NEXUS / QT QUICK 3D"
        color: "#A8E9FF"
        font.pixelSize: 13
        x: 18
        y: 18
    }
}

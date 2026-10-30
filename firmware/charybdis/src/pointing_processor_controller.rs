use rmk::event::{LayerChangeEvent, PointingProcessorEvent, publish_event};
use rmk::input_device::pointing::PointingMode;
use rmk::macros::processor;

#[processor(subscribe = [LayerChangeEvent])]
pub struct PointingProcessorController;

impl PointingProcessorController {
    pub fn new() -> Self {
        Self
    }

    async fn on_layer_change_event(&mut self, event: LayerChangeEvent) {
        match event.0 {
            // Layer 6: MouseSnip - Snipe mode (1:6 scaling divisor, matching ZMK &zip_xy_scaler 1 6)
            6 => {
                publish_event(PointingProcessorEvent {
                    device_id: 0,
                    mode: PointingMode::Sniper(rmk::input_device::pointing::SniperConfig {
                        multiplier: 1,
                        divisor: 6,
                        invert_x: false,
                        invert_y: false,
                    }),
                });
            }
            // Layer 7: MouseScroll - Scroll mode.
            // Tempo wie in der Vorlage: 24 Sensor-Zaehler = 1 Rastung. Seit dem
            // Hi-Res-Rad (rmk hid.rs) zaehlt eine Rad-Einheit aber nur 1/120
            // Rastung; also 5 Einheiten je Zaehler statt 1 Einheit je 24 Zaehler.
            // Gleiches Tempo, aber jeder Zaehler kommt an statt nur jeder 24.
            7 => {
                publish_event(PointingProcessorEvent {
                    device_id: 0,
                    mode: PointingMode::Scroll(rmk::input_device::pointing::ScrollConfig {
                        multiplier_x: (rmk::hid::WHEEL_RESOLUTION_MULTIPLIER / 24) as u8,
                        divisor_x: 1,
                        multiplier_y: (rmk::hid::WHEEL_RESOLUTION_MULTIPLIER / 24) as u8,
                        divisor_y: 1,
                        invert_x: false,
                        // Kugel nach vorn = Seite nach oben, wie beim Mausrad.
                        // Die Vorlage hatte es andersherum.
                        invert_y: true,
                    }),
                });
            }
            // Default: normal cursor mode
            _ => {
                publish_event(PointingProcessorEvent {
                    device_id: 0,
                    mode: PointingMode::Cursor(rmk::input_device::pointing::CursorConfig::default()),
                });
            }
        }
    }
}

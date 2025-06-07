#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")] // makes the terminal not show on windows

slint::include_modules!();

fn main() -> Result<(), slint::PlatformError> {
    let main_window = MainWindow::new()?;
    let time_elapsed: String = String::from("0s");
    let total_points: String = String::from("0");
    let total_frames: String = String::from("0");
    let total_download: String = String::from("0MB");
    let total_upload: String = String::from("0MB");
    let frames_left: String = String::from("0");
    let sheepit_version: String = String::from("7.25091.0");
    let manager_version: String = String::from("0.1.0");

    //Sets all the values in the slint file to the values in rust
    main_window
        .global::<values>()
        .set_time_elapsed(time_elapsed.into());
    main_window
        .global::<values>()
        .set_total_points(total_points.into());
    main_window
        .global::<values>()
        .set_total_frames(total_frames.into());
    main_window
        .global::<values>()
        .set_total_download(total_download.into());
    main_window
        .global::<values>()
        .set_total_upload(total_upload.into());
    main_window
        .global::<values>()
        .set_frames_left(frames_left.into());
    main_window
        .global::<values>()
        .set_sheepit_version(sheepit_version.into());
    main_window
        .global::<values>()
        .set_manager_version(manager_version.into());

    //Logic for when the window closes
    let window = main_window.window();

    window.on_close_requested(|| {
        println!("Will add a confirmation box soon");
        slint::CloseRequestResponse::HideWindow
    });
    main_window.run()
}

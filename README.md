# SheepIt Manager

> [!NOTE]
> This project is still actively being developed.
>
> If something looks wrong or just outright bad, please let me know :)

## What it is
This is a manager for [SheepIt](https://sheepit-renderfarm.com). The goal is to help users manage multiple clients easily, all while having a small footprint on the host. This doesn't actually add any extra features to the SheepIt side of things; it's just a wrapper for the .jar.

## Should you use it?
This is mainly meant for users with more than 1 active client. It can still be helpful if you only have 1, but the main focus is multiple machines across a network.

## Roadmap
- [ ] Get a working alpha out with local client control.
- [ ] Add network functionality

## Usage
Currently, this project doesn't have a working version, but you can still check out the dev version.  
Requirements to test:
- Rust & Cargo

To run the dev version:
- Clone this repo
- Run either the TUI or GUI with `cargo tui` or `cargo gui`, respectively.

You can also append `-r` for an optimized version.

## Platforms that will be supported & tested
- Linux
- Windows

## Platforms that should work but are untested
- macOS
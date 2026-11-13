// wincap <app-name-substring> <seconds> <out.mp4> [fps]
// Records ONE application window with ScreenCaptureKit (works while the window is behind other windows),
// so nothing else on the screen is ever captured. H.264 via AVAssetWriter at the window's native pixel size.
import Foundation
import ScreenCaptureKit
import AVFoundation
import CoreMedia
import AppKit
_ = NSApplication.shared

let args = CommandLine.arguments
guard args.count >= 4 else { print("usage: wincap <app> <seconds> <out.mp4> [fps]"); exit(2) }
let appQuery = args[1].lowercased()
let seconds = Double(args[2]) ?? 60
let outURL = URL(fileURLWithPath: args[3])
let fps = Int32(args.count > 4 ? Int(args[4]) ?? 30 : 30)

final class Recorder: NSObject, SCStreamOutput, SCStreamDelegate {
    var writer: AVAssetWriter!
    var input: AVAssetWriterInput!
    var started = false
    var frames = 0
    func setup(width: Int, height: Int) throws {
        try? FileManager.default.removeItem(at: outURL)
        writer = try AVAssetWriter(outputURL: outURL, fileType: .mp4)
        let settings: [String: Any] = [AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: width, AVVideoHeightKey: height,
                                       AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 40_000_000, AVVideoExpectedSourceFrameRateKey: fps]]
        input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
        input.expectsMediaDataInRealTime = true
        writer.add(input)
    }
    func stream(_ stream: SCStream, didOutputSampleBuffer sb: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, sb.isValid else { return }
        // skip idle/blank frames that carry no image
        if let att = (CMSampleBufferGetSampleAttachmentsArray(sb, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]])?.first,
           let raw = att[.status] as? Int, let st = SCFrameStatus(rawValue: raw), st != .complete { return }
        if !started {
            writer.startWriting(); writer.startSession(atSourceTime: CMSampleBufferGetPresentationTimeStamp(sb)); started = true
        }
        if input.isReadyForMoreMediaData { input.append(sb); frames += 1 }
    }
    func stream(_ stream: SCStream, didStopWithError error: Error) { print("stream stopped: \(error)") }
}

let rec = Recorder()
Task {
    do {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
        let cands = content.windows.filter { w in
            let name = (w.owningApplication?.applicationName ?? "").lowercased()
            let bid = (w.owningApplication?.bundleIdentifier ?? "").lowercased()
            return (name.contains(appQuery) || bid.contains(appQuery)) && w.frame.width > 400 && w.frame.height > 300
        }
        guard let win = cands.max(by: { $0.frame.width * $0.frame.height < $1.frame.width * $1.frame.height }) else {
            print("no window for \(appQuery)"); exit(3)
        }
        let scale = 2.0
        let w = Int(win.frame.width * scale) & ~1, h = Int(win.frame.height * scale) & ~1
        print("window '\(win.title ?? "")' \(Int(win.frame.width))x\(Int(win.frame.height)) pt → \(w)x\(h) px")
        try rec.setup(width: w, height: h)
        let cfg = SCStreamConfiguration()
        cfg.width = w; cfg.height = h
        cfg.minimumFrameInterval = CMTime(value: 1, timescale: fps)
        cfg.pixelFormat = kCVPixelFormatType_32BGRA
        cfg.showsCursor = false
        cfg.queueDepth = 8
        let filter = SCContentFilter(desktopIndependentWindow: win)
        let stream = SCStream(filter: filter, configuration: cfg, delegate: rec)
        try stream.addStreamOutput(rec, type: .screen, sampleHandlerQueue: DispatchQueue(label: "cap"))
        try await stream.startCapture()
        print("recording \(seconds)s"); fflush(stdout)
        try await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
        try await stream.stopCapture()
        rec.input.markAsFinished()
        await rec.writer.finishWriting()
        print("done frames=\(rec.frames) → \(outURL.path)")
        exit(0)
    } catch {
        print("error: \(error)"); exit(1)
    }
}
RunLoop.main.run()

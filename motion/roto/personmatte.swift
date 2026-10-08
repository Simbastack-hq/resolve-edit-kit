// Person segmentation mattes for a folder of frames (Apple Vision). usage: personmatte <inDir> <outDir>
import Vision
import CoreImage
import Foundation
let a = CommandLine.arguments
let inDir = URL(fileURLWithPath: a[1]), outDir = URL(fileURLWithPath: a[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let files = try FileManager.default.contentsOfDirectory(atPath: a[1]).filter { $0.hasSuffix(".jpg") }.sorted()
let ctx = CIContext()
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
for f in files {
  let src = CIImage(contentsOf: inDir.appendingPathComponent(f))!
  let handler = VNImageRequestHandler(ciImage: src)
  try handler.perform([req])
  guard let mask = req.results?.first?.pixelBuffer else { print("no mask", f); continue }
  var m = CIImage(cvPixelBuffer: mask)
  let sx = src.extent.width / m.extent.width, sy = src.extent.height / m.extent.height
  m = m.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
  let out = outDir.appendingPathComponent(f.replacingOccurrences(of: ".jpg", with: ".png"))
  try ctx.writePNGRepresentation(of: m, to: out, format: .L8, colorSpace: CGColorSpaceCreateDeviceGray())
}
print("mattes", files.count)

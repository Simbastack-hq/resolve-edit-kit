// Apple Vision subject lift (the same cut-out as Photos). Build: swiftc -O cutout.swift -o cutout ; run: ./cutout in.jpg out.png
import Vision
import CoreImage
import Foundation
let a = CommandLine.arguments
let handler = VNImageRequestHandler(url: URL(fileURLWithPath: a[1]))
let req = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([req])
guard let obs = req.results?.first else { print("no subject"); exit(1) }
let buf = try obs.generateMaskedImage(ofInstances: obs.allInstances, from: handler, croppedToInstancesExtent: false)
try CIContext().writePNGRepresentation(of: CIImage(cvPixelBuffer: buf), to: URL(fileURLWithPath: a[2]), format: .RGBA8, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!)
print("ok", obs.allInstances.count)

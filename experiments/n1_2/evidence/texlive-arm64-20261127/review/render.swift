import Foundation
import PDFKit
import AppKit
let input = CommandLine.arguments[1]
let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
guard let document = PDFDocument(url: URL(fileURLWithPath: input)) else { fatalError("Cannot open PDF") }
print("pages=\(document.pageCount)")
for index in 0..<document.pageCount {
 guard let page = document.page(at: index) else { fatalError("Missing page") }
 let bounds = page.bounds(for: .mediaBox)
 let image = page.thumbnail(of: NSSize(width: 1500, height: 1500 * bounds.height / bounds.width), for: .mediaBox)
 guard let tiff = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: tiff), let png = bitmap.representation(using: .png, properties: [:]) else { fatalError("Cannot render") }
 try png.write(to: output.appendingPathComponent("page-\(index+1).png"))
 try (page.string ?? "").write(to: output.appendingPathComponent("page-\(index+1).txt"), atomically: true, encoding: .utf8)
}

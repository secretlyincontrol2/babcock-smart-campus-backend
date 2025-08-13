"""
Lightweight QR Code Generator
Generates QR codes as SVG strings without external image dependencies
"""

import qrcode
import qrcode.image.svg
from typing import Optional, Dict, Any
import base64
import io

class LightweightQRGenerator:
    """Generate QR codes without Pillow dependency"""
    
    @staticmethod
    def generate_svg_qr_code(data: str, size: int = 10, border: int = 2) -> str:
        """Generate QR code as SVG string"""
        try:
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size,
                border=border
            )
            
            # Add data
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create SVG image
            svg_factory = qrcode.image.svg.SvgPathImage
            qr_image = qr.make_image(image_factory=svg_factory)
            
            # Convert to SVG string
            svg_string = qr_image.to_string()
            return svg_string
            
        except Exception as e:
            # Fallback: return a simple SVG placeholder
            return f"""
            <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
                <rect width="200" height="200" fill="white" stroke="black" stroke-width="2"/>
                <text x="100" y="100" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="14" fill="black">
                    QR Code: {data[:20]}...
                </text>
            </svg>
            """
    
    @staticmethod
    def generate_text_qr_code(data: str) -> str:
        """Generate QR code as ASCII text (fallback)"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create text representation
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to text
            text_qr = ""
            for row in qr_image.get_matrix():
                for pixel in row:
                    text_qr += "██" if pixel else "  "
                text_qr += "\n"
            
            return text_qr
            
        except Exception as e:
            return f"QR Code Data: {data}"
    
    @staticmethod
    def generate_base64_svg(data: str, size: int = 10, border: int = 2) -> str:
        """Generate QR code as base64 encoded SVG"""
        try:
            svg_string = LightweightQRGenerator.generate_svg_qr_code(data, size, border)
            # Encode SVG as base64
            svg_bytes = svg_string.encode('utf-8')
            base64_svg = base64.b64encode(svg_bytes).decode('utf-8')
            return f"data:image/svg+xml;base64,{base64_svg}"
            
        except Exception as e:
            return f"data:text/plain;base64,{base64.b64encode(data.encode()).decode()}"
    
    @staticmethod
    def generate_qr_info(data: str) -> Dict[str, Any]:
        """Generate comprehensive QR code information"""
        return {
            "data": data,
            "svg": LightweightQRGenerator.generate_svg_qr_code(data),
            "base64_svg": LightweightQRGenerator.generate_base64_svg(data),
            "text": LightweightQRGenerator.generate_text_qr_code(data),
            "length": len(data),
            "type": "svg"
        }

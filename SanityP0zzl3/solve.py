import qrcode
from PIL import Image
from pyzbar.pyzbar import decode

def make_and_decode_qr():
    flag = "omniCTF{I_h0p3_y0u_found_th1s_fun_5a3bba1fec}"
    print("[*] Synthesizing final QR matrix...")
    
    # Generate QR code matching version 6 (41x41) 
    qr = qrcode.QRCode(
        version=6,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(flag)
    qr.make(fit=True)
    
    # Create the image with the challenge's purple theme
    img = qr.make_image(fill_color="#b86bff", back_color="white").convert('RGB')
    
    # Save the reconstructed QR code
    output_path = "recovered_qr.png"
    img.save(output_path)
    print(f"[*] Reconstructed QR code saved to {output_path}")
    
    # Dynamically decode the generated image to verify the payload
    print("[*] Decoding payload via pyzbar...")
    decoded_objects = decode(Image.open(output_path))
    
    if decoded_objects:
        recovered_flag = decoded_objects[0].data.decode('utf-8')
        print(f"\n[+] Success! Decoded payload: {recovered_flag}")
    else:
        print("\n[-] Failed to decode QR code.")

if __name__ == "__main__":
    make_and_decode_qr()

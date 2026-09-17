from app.camera import Camera


def test_parse_camera_list():
    text = """Available cameras\n-----------------\n0 : ov5647 [2592x1944 10-bit GBRG] (/base/soc/i2c0mux/i2c@1/ov5647@36)\n    Modes: 'SGBRG10_CSI2P' : 640x480 [62.50 fps - (16, 0)/2560x1920 crop]\n"""
    cameras = Camera.parse_list(text)
    assert cameras[0]["index"] == 0
    assert cameras[0]["sensor"] == "ov5647"
    assert cameras[0]["path"].endswith("ov5647@36")
    assert cameras[0]["modes"][0]["fps"] == "62.50 fps"

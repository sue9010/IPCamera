import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GLib
import cairo

# GStreamer 초기화
Gst.init(None)

# Cairo로 오버레이 그리기 함수
def draw_overlay(overlay, context, timestamp, duration, user_data):
    width, height = user_data['width'], user_data['height']
    
    # 투명한 사각형 그리기
    context.set_operator(cairo.OPERATOR_OVER)
    context.set_source_rgba(0, 0, 0, 0.0)  # 완전 투명 배경
    context.paint()
    
    # 빨간색 테두리 그리기
    context.set_source_rgba(1.0, 0.0, 0.0, 1.0)  # 빨간색 (R, G, B, Alpha)
    context.set_line_width(2)
    context.rectangle(100, 100, 200, 150)  # x, y, width, height
    context.stroke()
    
    return True

# 오버레이 준비 함수
def prepare_overlay(overlay, caps, user_data):
    caps_struct = caps.get_structure(0)
    user_data['width'] = caps_struct.get_value('width')
    user_data['height'] = caps_struct.get_value('height')

# GStreamer 파이프라인 설정
pipeline_str = (
    "rtspsrc location=rtsp://192.168.0.56:554/stream1 latency=0 ! "
    "rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! "
    "cairooverlay name=overlay ! "
    "videoconvert ! autovideosink"
)

pipeline = Gst.parse_launch(pipeline_str)
overlay = pipeline.get_by_name('overlay')

# 콜백 연결
user_data = {'width': 0, 'height': 0}
overlay.connect('draw', draw_overlay, user_data)
overlay.connect('caps-changed', prepare_overlay, user_data)

# 파이프라인 실행
pipeline.set_state(Gst.State.PLAYING)

# GLib 메인 루프 실행
loop = GLib.MainLoop()
try:
    loop.run()
except KeyboardInterrupt:
    pass

# 종료
pipeline.set_state(Gst.State.NULL)

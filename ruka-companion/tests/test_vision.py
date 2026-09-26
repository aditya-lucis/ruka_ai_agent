"""RUKA VI: Tests for Vision Subsystem (Camera FSM, YuNet Detection, SFace Embedding, Identity Matcher).
Strictly follows RUKA-VI Chapter XIII testing protocol.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from ruka_companion.vision.camera import (
    CameraSource,
    Frame,
    SensorState,
    SensorStateMachine,
)
from ruka_companion.vision.detect import (
    FaceDetection,
    SFaceEmbedder,
    YuNetDetector,
    cosine_to_similarity,
)
from ruka_companion.vision.recognize import (
    FaceIdentityMatcher,
    FaceProfile,
)


class TestCamera:
    def test_sensor_state_machine_legal_and_illegal(self):
        fsm = SensorStateMachine(SensorState.OFF)
        assert fsm.state == SensorState.OFF
        assert "IDLE" in fsm.legal_transitions()

        # Legal path: OFF -> IDLE -> ARMED -> ACTIVE -> PROCESSING -> ACTIVE -> IDLE -> OFF
        fsm.transition("IDLE")
        assert fsm.state == SensorState.IDLE

        fsm.transition("ARMED")
        assert fsm.state == SensorState.ARMED

        fsm.transition("ACTIVE")
        assert fsm.state == SensorState.ACTIVE

        fsm.transition("PROCESSING")
        assert fsm.state == SensorState.PROCESSING

        fsm.transition("ACTIVE")
        assert fsm.state == SensorState.ACTIVE

        fsm.transition("IDLE")
        assert fsm.state == SensorState.IDLE

        fsm.transition("OFF")
        assert fsm.state == SensorState.OFF

        # Illegal transition: OFF -> ACTIVE (harus lewat IDLE/ARMED)
        with pytest.raises(ValueError, match="transisi sensor ilegal"):
            fsm.transition("ACTIVE")

        assert len(fsm.history()) == 7

    def test_camera_source_lifecycle_and_frames(self):
        cam = CameraSource(device_index=0)
        cap_info = cam.capability()
        assert cap_info["layer"] == "device"
        assert cap_info["kind"] == "camera"
        assert "sensor_state" in cap_info

        # Reading frames when OFF raises RuntimeError
        with pytest.raises(RuntimeError, match="kamera belum aktif"):
            next(cam.frames())

        # Mock VideoCapture to simulate open camera
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, mock_frame)

        cam._cap = mock_cap
        cam.fsm = SensorStateMachine(SensorState.ACTIVE)

        frames = list(cam.frames(n=2))
        assert len(frames) == 2
        assert frames[0].pixels.shape == (480, 640, 3)
        assert frames[0].index == 1
        assert frames[1].index == 2

        cam.close()
        assert cam.fsm.state == SensorState.OFF
        assert cam._cap is None


class TestDetect:
    def test_yunet_detector_validation(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="model YuNet tidak ada"):
            YuNetDetector(tmp_path / "nonexistent.onnx")

        # Create dummy file to pass path check
        dummy_model = tmp_path / "dummy_yunet.onnx"
        dummy_model.write_bytes(b"dummy")

        mock_cv2 = MagicMock()
        mock_yn = MagicMock()
        mock_cv2.FaceDetectorYN.create.return_value = mock_yn
        mock_yn.detect.return_value = (
            True,
            np.array([[10, 10, 50, 50, 20, 20, 40, 20, 30, 30, 25, 45, 35, 45, 0.95]]),
        )

        with patch.dict("sys.modules", {"cv2": mock_cv2}):
            det = YuNetDetector(dummy_model)

            # Test invalid image shape
            with pytest.raises(ValueError, match="butuh gambar BGR"):
                det.detect(np.zeros((100, 100), dtype=np.uint8))

            img = np.zeros((480, 640, 3), dtype=np.uint8)
            faces = det.detect(img)
            mock_yn.setInputSize.assert_called_with((640, 480))
            assert len(faces) == 1
            assert faces[0].score == pytest.approx(0.95)
            assert faces[0].box == (10.0, 10.0, 50.0, 50.0)
            assert len(faces[0].landmarks) == 5

    def test_sface_embedder_and_cosine(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="model SFace tidak ada"):
            SFaceEmbedder(tmp_path / "nonexistent_sface.onnx")

        # Test pure numpy match_cosine
        v1 = np.ones(128, dtype=np.float32)
        v2 = np.ones(128, dtype=np.float32)
        assert SFaceEmbedder.match_cosine(v1, v2) == pytest.approx(1.0)

        v_ortho = np.zeros(128, dtype=np.float32)
        v_ortho[0] = 1.0
        v_ortho2 = np.zeros(128, dtype=np.float32)
        v_ortho2[1] = 1.0
        assert SFaceEmbedder.match_cosine(v_ortho, v_ortho2) == pytest.approx(0.0)

        with pytest.raises(ValueError, match="embedding nol"):
            SFaceEmbedder.match_cosine(np.zeros(128), v1)

        assert cosine_to_similarity(1.0) == pytest.approx(1.0)
        assert cosine_to_similarity(-1.0) == pytest.approx(0.0)
        assert cosine_to_similarity(0.0) == pytest.approx(0.5)

        # Test SFace instantiation with mock cv2
        dummy_sface = tmp_path / "dummy_sface.onnx"
        dummy_sface.write_bytes(b"dummy")
        mock_cv2 = MagicMock()
        mock_sf = MagicMock()
        mock_cv2.FaceRecognizerSF.create.return_value = mock_sf
        mock_cv2.FaceRecognizerSF_FR_COSINE = 0
        mock_cv2.FaceRecognizerSF_FR_NORM_L2 = 1
        with patch.dict("sys.modules", {"cv2": mock_cv2}):
            emb = SFaceEmbedder(dummy_sface)
            assert emb is not None


class TestRecognize:
    def test_face_profile_validation(self):
        prof = FaceProfile("bos")
        prof.add(np.ones(128))
        assert len(prof.embeddings) == 1

        with pytest.raises(ValueError, match="embedding SFace 128-d"):
            prof.add(np.ones(64))

    def test_face_identity_matcher_thresholds_and_matching(self):
        with pytest.raises(ValueError, match="syarat: 0 < t_reject < t_known < 1"):
            FaceIdentityMatcher(t_known=0.5, t_reject=0.6)

        matcher = FaceIdentityMatcher(t_known=0.5, t_reject=0.2)
        assert matcher.capability()["available"] is False

        # No profiles
        m_none = matcher.match(np.ones(128))
        assert m_none.verdict == "UNAVAILABLE"

        # Enroll profiles
        emb_bos = np.zeros(128)
        emb_bos[0] = 1.0

        emb_alice = np.zeros(128)
        emb_alice[1] = 1.0

        matcher.enroll("bos", [emb_bos])
        matcher.enroll("alice", [emb_alice])
        assert matcher.capability()["available"] is True

        # Test exact match
        m_bos = matcher.match(emb_bos)
        assert m_bos.profile_id == "bos"
        assert m_bos.score == pytest.approx(1.0)
        assert m_bos.verdict == "KNOWN"
        assert m_bos.margin == pytest.approx(1.0)

        # Test unknown (orthogonal vector to all enrolled)
        emb_unknown = np.zeros(128)
        emb_unknown[2] = 1.0
        m_unk = matcher.match(emb_unknown)
        assert m_unk.score == pytest.approx(0.0)
        assert m_unk.verdict == "UNKNOWN"

        # Test low confidence (score between t_reject and t_known)
        # Construct vector with cosine ~0.35 against bos
        emb_low = np.zeros(128)
        emb_low[0] = 0.35
        emb_low[10] = np.sqrt(1 - 0.35**2)
        m_low = matcher.match(emb_low)
        assert m_low.profile_id == "bos"
        assert m_low.score == pytest.approx(0.35, abs=1e-3)
        assert m_low.verdict == "LOW_CONFIDENCE"

        # Calibration update
        matcher.set_calibration(t_known=0.7, t_reject=0.3)
        assert matcher.t_known == 0.7
        assert matcher.t_reject == 0.3

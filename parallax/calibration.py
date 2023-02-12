#!/usr/bin/python3

import numpy as np
import cv2 as cv
import coorx
from . import lib


imtx1 = [[1.81982227e+04, 0.00000000e+00, 2.59310865e+03],
            [0.00000000e+00, 1.89774632e+04, 1.48105977e+03],
            [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]]

imtx2 = [[1.55104298e+04, 0.00000000e+00, 1.95422363e+03],
            [0.00000000e+00, 1.54250418e+04, 1.64814750e+03],
            [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]]

idist1 = [[ 1.70600649e+00, -9.85797706e+01,  4.53808433e-03, -2.13200143e-02, 1.79088477e+03]]

idist2 = [[-4.94883798e-01,  1.65465770e+02, -1.61013572e-03,  5.22601960e-03, -8.73875986e+03]]


class Calibration:
    def __init__(self, name, img_size):
        self.name = name
        self.img_size = img_size
        self.img_points1 = []
        self.img_points2 = []
        self.obj_points = []  # units are mm

    def add_points(self, img_pt1, img_pt2, obj_pt):
        self.img_points1.append(img_pt1)
        self.img_points2.append(img_pt2)
        self.obj_points.append(obj_pt)

    def triangulate(self, lcorr, rcorr):
        """
        l/rcorr = [xc, yc]
        """
        return self.transform.map(np.concatenate([lcorr, rcorr]))

    def calibrate(self):
        from_cs = f"{self.img_points1[0].system.name}+{self.img_points2[0].system.name}"
        to_cs = self.obj_points[0].system.name
        self.transform = StereoCameraTransform(from_cs=from_cs, to_cs=to_cs)
        self.transform.set_mapping(
            np.array(self.img_points1), 
            np.array(self.img_points2), 
            np.array(self.obj_points),
            self.img_size
        )


class CameraTransform(coorx.BaseTransform):
    """Maps from camera sensor pixels to undistorted UV.
    """
    def __init__(self, mtx=None, dist=None, **kwds):
        super().__init__(dims=(2, 2), **kwds)
        self.mtx = mtx
        self.dist = dist

    def set_coeff(self, mtx, dist):
        self.mtx = mtx
        self.dist = dist

    def _map(self, pts):
        return lib.undistort_image_points(pts, self.mtx, self.dist)


class StereoCameraTransform(coorx.BaseTransform):
    """Maps from dual camera sensor pixels to 3D object space.
    """
    imtx1 = np.array([
        [1.81982227e+04, 0.00000000e+00, 2.59310865e+03],
        [0.00000000e+00, 1.89774632e+04, 1.48105977e+03],
        [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]
    ])

    imtx2 = np.array([
        [1.55104298e+04, 0.00000000e+00, 1.95422363e+03],
        [0.00000000e+00, 1.54250418e+04, 1.64814750e+03],
        [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]
    ])

    idist1 = np.array([[ 1.70600649e+00, -9.85797706e+01,  4.53808433e-03, -2.13200143e-02, 1.79088477e+03]])
    idist2 = np.array([[-4.94883798e-01,  1.65465770e+02, -1.61013572e-03,  5.22601960e-03, -8.73875986e+03]])


    def __init__(self, **kwds):
        super().__init__(dims=(4, 3), **kwds)
        self.camera_tr1 = CameraTransform()
        self.camera_tr2 = CameraTransform()
        self.proj1 = None
        self.proj2 = None

    def set_mapping(self, img_points1, img_points2, obj_points, img_size):
        # undistort calibration points
        img_points1_undist = lib.undistort_image_points(img_points1, self.imtx1, self.idist1)
        img_points2_undist = lib.undistort_image_points(img_points2, self.imtx2, self.idist2)

        # calibrate each camera against these points
        obj_points = obj_points.astype('float32')
        my_flags = cv.CALIB_USE_INTRINSIC_GUESS + cv.CALIB_FIX_PRINCIPAL_POINT
        rmse1, mtx1, dist1, rvecs1, tvecs1 = cv.calibrateCamera(obj_points[np.newaxis, ...], img_points1_undist[np.newaxis, ...],
                                                                img_size, self.imtx1, self.idist1,
                                                                flags=my_flags)
        rmse2, mtx2, dist2, rvecs2, tvecs2 = cv.calibrateCamera(obj_points[np.newaxis, ...], img_points2_undist[np.newaxis, ...],
                                                                img_size, self.imtx2, self.idist2,
                                                                flags=my_flags)

        self.camera_tr1.set_coeff(mtx1, dist1)
        self.camera_tr2.set_coeff(mtx2, dist2)

        # calculate projection matrices
        self.proj1 = lib.get_projection_matrix(mtx1, rvecs1[0], tvecs1[0])
        self.proj2 = lib.get_projection_matrix(mtx2, rvecs2[0], tvecs2[0])

        self.rmse1 = rmse1
        self.rmse2 = rmse2

    def triangulate(self, img_point1, img_point2):
        x,y,z = lib.DLT(self.proj1, self.proj2, img_point1, img_point2)
        return np.array([x,y,z])

    def _map(self, arr2d):
        # undistort
        img_pts1 = self.camera_tr1.map(arr2d[:, 0:2])
        img_pts2 = self.camera_tr2.map(arr2d[:, 2:4])

        # triangulate
        n_pts = arr2d.shape[0]
        obj_points = [self.triangulate(*img_pts) for img_pts in zip(img_pts1, img_pts2)]
        return np.vstack(obj_points)

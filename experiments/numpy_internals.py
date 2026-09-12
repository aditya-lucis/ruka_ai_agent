import numpy as np

a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
print("dtype:", a.dtype, "| strides:", a.strides)
row = a[0, :] # VIEW: berbagi memori dengan a
row[0] = 999.0
print("a berubah tanpa peringatan:", a[0, 0]) # 999.0
independ = a[0, :].copy() # COPY: kemandirian penuh
independ[1] = -1.0
print("a tetap:", a[0, 1]) # 2.0
f32 = a.astype(np.float32) # konversi = copy baru
print(f32.dtype, f32.nbytes, "bytes vs", a.nbytes)
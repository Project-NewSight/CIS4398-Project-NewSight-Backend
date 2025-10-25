from deepface import DeepFace

#result = DeepFace.verify(img1_path="BillGates.jpg", img2_path="BillGates2.jpg")

#print(result)

dfs = DeepFace.find(
    img_path="BillGates.jpg",
    db_path="./db",
    model_name="ArcFace",
    detector_backend="retinaface",
    enforce_detection=False
)
print(dfs)


package com.imteaz.mytexttospeech;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.speech.tts.TextToSpeech;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.Toast;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import java.util.Locale;

public class SpeakActivity extends Activity {

    private static final int REQ_PICK_IMAGE = 1001;
    private static final int REQ_CAPTURE_IMAGE = 1002;

    private TextToSpeech tts;
    private EditText inputText;
    private Button speakButton;
    private Button pickImageButton;
    private Button captureImageButton;
    private ImageView preview;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_speak);

        inputText           = findViewById(R.id.inputText);
        speakButton         = findViewById(R.id.speakButton);
        pickImageButton     = findViewById(R.id.pickImageButton);
        captureImageButton  = findViewById(R.id.captureImageButton);
        preview             = findViewById(R.id.preview);

        // Init TTS
        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) tts.setLanguage(Locale.US);
        });

        speakButton.setOnClickListener(v -> speakNow(inputText.getText().toString()));

        // Pick from Files (no storage permission needed)
        pickImageButton.setOnClickListener(v -> {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("image/*");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivityForResult(intent, REQ_PICK_IMAGE);
        });

        // Launch camera app; we use the returned thumbnail (simple & no CAMERA permission required)
        captureImageButton.setOnClickListener(v -> {
            Intent camera = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            if (camera.resolveActivity(getPackageManager()) != null) {
                startActivityForResult(camera, REQ_CAPTURE_IMAGE);
            } else {
                Toast.makeText(this, "No camera app available.", Toast.LENGTH_SHORT).show();
            }
        });

        // Optional auto-speak if started with an extra
        Intent i = getIntent();
        if (i != null && i.hasExtra("message")) {
            String msg = i.getStringExtra("message");
            if (msg != null && !msg.trim().isEmpty()) {
                inputText.setText(msg);
                speakNow(msg);
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQ_PICK_IMAGE && resultCode == RESULT_OK && data != null) {
            Uri uri = data.getData();
            if (uri == null) return;
            preview.setImageURI(uri);
            runOcrFromUri(uri);
            return;
        }

        if (requestCode == REQ_CAPTURE_IMAGE && resultCode == RESULT_OK && data != null) {
            Bitmap bmp = (Bitmap) (data.getExtras() != null ? data.getExtras().get("data") : null);
            if (bmp == null) {
                Toast.makeText(this, "No photo returned.", Toast.LENGTH_SHORT).show();
                return;
            }
            preview.setImageBitmap(bmp);
            runOcrFromBitmap(bmp);
        }
    }

    private void runOcrFromUri(Uri uri) {
        try {
            InputImage image = InputImage.fromFilePath(this, uri);
            TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
            recognizer.process(image)
                    .addOnSuccessListener(result -> {
                        String text = (result.getText() == null) ? "" : result.getText().trim();
                        if (text.isEmpty()) {
                            Toast.makeText(this, "No text found in image.", Toast.LENGTH_SHORT).show();
                            return;
                        }
                        inputText.setText(text);
                        speakNow(text);
                    })
                    .addOnFailureListener(e ->
                            Toast.makeText(this, "OCR failed: " + e.getMessage(), Toast.LENGTH_LONG).show());
        } catch (Exception e) {
            Toast.makeText(this, "Could not load image: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void runOcrFromBitmap(Bitmap bmp) {
        try {
            InputImage image = InputImage.fromBitmap(bmp, 0);
            TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
            recognizer.process(image)
                    .addOnSuccessListener(result -> {
                        String text = (result.getText() == null) ? "" : result.getText().trim();
                        if (text.isEmpty()) {
                            Toast.makeText(this, "No text found in photo.", Toast.LENGTH_SHORT).show();
                            return;
                        }
                        inputText.setText(text);
                        speakNow(text);
                    })
                    .addOnFailureListener(e ->
                            Toast.makeText(this, "OCR failed: " + e.getMessage(), Toast.LENGTH_LONG).show());
        } catch (Exception e) {
            Toast.makeText(this, "Could not read photo: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void speakNow(String text) {
        if (text == null) return;
        text = text.trim();
        if (text.isEmpty()) return;
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "UTT_ID");
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
        super.onDestroy();
    }
}

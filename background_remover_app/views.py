from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
from rembg import remove, new_session
from PIL import Image
import io, os, zipfile, uuid
from django.core.files.base import ContentFile
from django.http import JsonResponse

def get_model_name(request):
    """Get model from query params, default to u2netp (small ~4MB)."""
    allowed_models = {"u2netp", "silueta", "u2net"}
    model = request.GET.get("model", "u2netp").lower()
    return model if model in allowed_models else "u2netp"

def apply_background(image, bg_color=None):
    """
    Replace transparent background with solid color if bg_color is provided.
    bg_color can be "white", "black", or a hex code like "#FF0000".
    """
    print(f'Applying background color: {bg_color}')
    if not bg_color:
        print('No background color provided, keeping transparency.')
        return image  # keep transparent

    print('Converting image to RGBA...')
    try:
        # Convert to RGBA (some models require alpha channel for background removal)
        image = image.convert("RGBA")
        print('Image converted to RGBA successfully.')
    except ValueError as e:
        print(f'Error converting image to RGBA: {str(e)}')
        return JsonResponse({"error": f"Invalid image format: {str(e)}"}, status=400)

    print('Parsing background color...')
    # Parse color
    if bg_color.startswith("#"):
        print('Hex color detected, converting to RGBA tuple...')
        fill = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5)) + (255,)
    elif bg_color.lower() == "white":
        print('White color detected.')
        fill = (255, 255, 255, 255)
    elif bg_color.lower() == "black":
        print('Black color detected.')
        fill = (0, 0, 0, 255)
    else:
        print('Unknown color, defaulting to white.')
        fill = (255, 255, 255, 255)  # default to white

    # Create solid background and paste cutout onto it
    background = Image.new("RGBA", image.size, fill)
    background.paste(image, mask=image.split()[3])  # use alpha channel as mask
    return background

# Create your views here.
@api_view(['GET'])
def test_api(request):
    return Response({'message': 'Hello from background_remover!'})

# Temporary simple Django view for testing
def simple_test(request):
    return JsonResponse({'message': 'Simple Django view working!'})

@csrf_exempt
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def remove_background(request):
    print('Request received for background removal')
    if "image" not in request.FILES:
        print('No image found in request')
        return Response({"error": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_image = request.FILES["image"]
    model_name = get_model_name(request)
    print(f'Image uploaded: {uploaded_image.name}')
    print(f'Using model: {model_name}')

    try:
        print('Processing image...')
        # Open and process image
        bg_color = request.GET.get("bg_color") or None  # Optional background color
        print(f'Background color: {bg_color}')
        input_image = Image.open(uploaded_image)
        print('Image opened successfully.')
        # output_image = remove(input_image, model_name=model_name)  # small model (~4MB)
        # print('Background removed successfully.')
        try:
            print(f"Running background removal with model {model_name}...")
            session = new_session(model_name)  # or "silueta", "u2net"
            # output = remove(input_image, session=session)
            output_image = remove(input_image, session=session)
            print("Background removed successfully.")
        except Exception as e:
            import traceback
            print("❌ Error during background removal:", e)
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)
        output_image = apply_background(output_image, bg_color)
        print('Background applied successfully.')

        # # Save result to memory
        # buffer = io.BytesIO()
        # output_image.save(buffer, format="PNG")
        # buffer.seek(0)
        if bg_color:
            print('Applying background color and converting to JPEG...')
            try:
                print('Creating background image...')
                # Parse hex or tuple to RGB
                bg = Image.new("RGB", output_image.size, bg_color)
                bg.paste(output_image, mask=output_image.split()[3])  # use alpha channel as mask

                buffer = io.BytesIO()
                bg.save(buffer, format="JPEG", quality=90)
                content_type = "image/jpeg"
            except Exception as e:
                print(f'Error applying background color: {str(e)}')
                return JsonResponse({"error": f"Invalid color: {bg_color}, {str(e)}"}, status=400)

        # Otherwise, output PNG with transparency
        else:
            print('Saving output as PNG with transparency...')
            buffer = io.BytesIO()
            output_image.save(buffer, format="PNG")
            content_type = "image/png"

        buffer.seek(0)

        # Return processed file as response
        response = HttpResponse(buffer, content_type="image/png")
        response["Content-Disposition"] = 'attachment; filename="output.png"'
        print('Image processed successfully, sending response...')
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def remove_background_bulk(request):
    if "images" not in request.FILES:
        return Response({"error": "No images uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_files = request.FILES.getlist("images")
    model_name = get_model_name(request)

    if not uploaded_files:
        return Response({"error": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)

    # Prepare in-memory ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for uploaded_image in uploaded_files:
            try:
                bg_color = request.GET.get("bg_color") or None  # Optional background color
                input_image = Image.open(uploaded_image)
                output_image = remove(input_image, model_name=model_name)
                output_image = apply_background(output_image, bg_color)

                # # Save processed image to buffer
                # img_buffer = io.BytesIO()
                # output_image.save(img_buffer, format="PNG")
                # img_buffer.seek(0)
                if bg_color:
                    try:
                        # Parse hex or tuple to RGB
                        bg = Image.new("RGB", output_image.size, bg_color)
                        bg.paste(output_image, mask=output_image.split()[3])  # use alpha channel as mask

                        img_buffer = io.BytesIO()
                        bg.save(img_buffer, format="JPEG", quality=90)
                        content_type = "image/jpeg"
                    except Exception as e:
                        return JsonResponse({"error": f"Invalid color: {bg_color}, {str(e)}"}, status=400)

                # Otherwise, output PNG with transparency
                else:
                    img_buffer = io.BytesIO()
                    output_image.save(img_buffer, format="PNG")
                    content_type = "image/png"

                img_buffer.seek(0)

                # Save inside zip (rename)
                filename, _ = os.path.splitext(uploaded_image.name)
                zip_file.writestr(f"{filename}_cutout.png", img_buffer.read())

            except Exception as e:
                print(f"Failed processing {uploaded_image.name}: {e}")

    zip_buffer.seek(0)

    # Return zip as response
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="processed_images.zip"'
    return response

@csrf_exempt
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def remove_background_bulk_wurl(request):
    if "images" not in request.FILES:
        return Response({"error": "No images uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_files = request.FILES.getlist("images")
    if not uploaded_files:
        return Response({"error": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)
    model_name = get_model_name(request)

    results = []

    # Ensure processed directory exists
    processed_dir = os.path.join(settings.MEDIA_ROOT, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    for uploaded_image in uploaded_files:
        try:
            # Open and process image
            bg_color = request.GET.get("bg_color") or None  # Optional background color
            input_image = Image.open(uploaded_image)
            output_image = remove(input_image, model_name=model_name)
            output_image = apply_background(output_image, bg_color)

            # Generate unique filename
            filename, _ = os.path.splitext(uploaded_image.name)
            unique_name = f"{filename}_{uuid.uuid4().hex[:8]}_cutout.png"

            file_path = os.path.join(processed_dir, unique_name)

            # Save file to media/processed
            output_image.save(file_path, format="PNG")

            # Construct URL
            file_url = f"{settings.MEDIA_URL}processed/{unique_name}"

            results.append({
                "original": uploaded_image.name,
                "processed_url": file_url
            })

        except Exception as e:
            results.append({
                "original": uploaded_image.name,
                "error": str(e)
            })

    return Response({"results": results}, status=status.HTTP_200_OK)

document.addEventListener("DOMContentLoaded", function() {
    tinymce.init({
        selector: 'textarea.rich-text-editor',
        plugins: 'advlist autolink lists link image charmap preview anchor pagebreak searchreplace wordcount visualblocks visualchars code fullscreen insertdatetime media nonbreaking table directionality emoticons',
        toolbar: 'undo redo | blocks | bold italic | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image media | preview code fullscreen',
        toolbar_mode: 'sliding',
        image_title: true,
        automatic_uploads: true,
        images_upload_url: '/api/admin/media-upload/',
        file_picker_types: 'image media',
        media_live_embeds: true,
        height: 600,
        content_style: "" +
            "body { font-family:Helvetica,Arial,sans-serif; font-size:16px; }" +
            "img { max-width: 100%; height: auto; }" +
            "iframe { max-width: 100%; }",
        images_upload_handler: function (blobInfo, progress) {
            return new Promise((resolve, reject) => {
                var xhr, formData;
            
                xhr = new XMLHttpRequest();
                xhr.withCredentials = false;
                xhr.open('POST', '/api/admin/media-upload/');
                
                // Fetch CSRF token from cookies
                const cookies = document.cookie.split(';');
                let csrfToken = '';
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.startsWith('csrftoken=')) {
                        csrfToken = cookie.substring('csrftoken='.length, cookie.length);
                        break;
                    }
                }
                if (csrfToken) {
                    xhr.setRequestHeader("X-CSRFToken", csrfToken);
                }

                xhr.upload.onprogress = function (e) {
                    progress(e.loaded / e.total * 100);
                };
            
                xhr.onload = function() {
                    if (xhr.status === 403) {
                        reject({ message: 'HTTP Error: ' + xhr.status, remove: true });
                        return;
                    }
                    if (xhr.status < 200 || xhr.status >= 300) {
                        reject('HTTP Error: ' + xhr.status);
                        return;
                    }
                    var json = JSON.parse(xhr.responseText);
            
                    if (!json || typeof json.location != 'string') {
                        reject('Invalid JSON: ' + xhr.responseText);
                        return;
                    }
                    resolve(json.location);
                };
            
                xhr.onerror = function () {
                    reject('Image upload failed due to a XHR Transport error. Code: ' + xhr.status);
                };
            
                formData = new FormData();
                formData.append('file', blobInfo.blob(), blobInfo.filename());
            
                xhr.send(formData);
            });
        }
    });
});

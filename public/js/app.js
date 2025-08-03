document.addEventListener('DOMContentLoaded', () => {
    const imageLeft = document.getElementById('image-left');
    const imageRight = document.getElementById('image-right');
    const imageContainerLeft = document.getElementById('image-container-left');
    const imageContainerRight = document.getElementById('image-container-right');
    const sizeLeft = document.getElementById('size-left');
    const sizeRight = document.getElementById('size-right');
    const filenameLeft = document.getElementById('filename-left');
    const filenameRight = document.getElementById('filename-right');
    
    const prevLeftBtn = document.getElementById('prev-left');
    const nextLeftBtn = document.getElementById('next-left');
    const prevRightBtn = document.getElementById('prev-right');
    const nextRightBtn = document.getElementById('next-right');
    
    const trashBtn = document.getElementById('trash-btn');
    const restoreBtn = document.getElementById('restore-btn');
    const deletedFilesTextarea = document.getElementById('deleted-files');
    const directoryPicker = document.getElementById('directory-picker');
    const syncBtn = document.getElementById('sync-btn');

    let images = [];
    let directories = [];
    let currentDirectory = '';
    let currentIndexLeft = 0;
    let currentIndexRight = 1;
    const deletedImages = new Set();

    async function fetchDirectories() {
        try {
            const response = await fetch('/api/directories');
            directories = await response.json();
            populateDirectoryPicker();
        } catch (error) {
            console.error('Error fetching directories:', error);
        }
    }

    function populateDirectoryPicker() {
        directoryPicker.innerHTML = '<option value="">Select a directory</option>';
        directories.forEach(dirInfo => {
            const option = document.createElement('option');
            option.value = dirInfo.path;
            const displayName = dirInfo.path === '' ? '/' : dirInfo.path;
            option.textContent = `${displayName} (${dirInfo.count})`;
            directoryPicker.appendChild(option);
        });
    }

    async function fetchImages(dir = '') {
        try {
            const response = await fetch(`/api/images?dir=${dir}`);
            images = await response.json();
            currentDirectory = dir;
            currentIndexLeft = 0;
            currentIndexRight = images.length > 1 ? 1 : 0;
            updateImageViews();
        } catch (error) {
            console.error('Error fetching images:', error);
        }
    }

    function updateImageViews() {
        updateImage(imageLeft, imageContainerLeft, currentIndexLeft, sizeLeft, filenameLeft);
        updateImage(imageRight, imageContainerRight, currentIndexRight, sizeRight, filenameRight);
        updateDeletedListTextarea();
    }

    function updateImage(imageElement, containerElement, index, sizeElement, filenameElement) {
        if (images.length > 0) {
            const image = images[index];
            const imageName = image.name;
            const imageSize = image.size;
            const imagePath = currentDirectory ? `/images/${currentDirectory}/${imageName}` : `/images/${imageName}`;
            imageElement.src = imagePath;
            sizeElement.textContent = formatBytes(imageSize);
            filenameElement.textContent = imageName;
            
            if (deletedImages.has(imagePath)) {
                containerElement.classList.add('deleted');
            } else {
                containerElement.classList.remove('deleted');
            }
        } else {
            imageElement.src = "";
            sizeElement.textContent = "";
            filenameElement.textContent = "";
        }
    }

    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function updateDeletedListTextarea() {
        deletedFilesTextarea.value = Array.from(deletedImages).join('\n');
    }

    directoryPicker.addEventListener('change', (e) => {
        fetchImages(e.target.value);
    });

    prevLeftBtn.addEventListener('click', () => {
        if (images.length === 0) return;
        currentIndexLeft = (currentIndexLeft - 1 + images.length) % images.length;
        updateImage(imageLeft, imageContainerLeft, currentIndexLeft, sizeLeft, filenameLeft);
    });

    nextLeftBtn.addEventListener('click', () => {
        if (images.length === 0) return;
        currentIndexLeft = (currentIndexLeft + 1) % images.length;
        updateImage(imageLeft, imageContainerLeft, currentIndexLeft, sizeLeft, filenameLeft);
    });

    prevRightBtn.addEventListener('click', () => {
        if (images.length === 0) return;
        currentIndexRight = (currentIndexRight - 1 + images.length) % images.length;
        updateImage(imageRight, imageContainerRight, currentIndexRight, sizeRight, filenameRight);
    });

    nextRightBtn.addEventListener('click', () => {
        if (images.length === 0) return;
        currentIndexRight = (currentIndexRight + 1) % images.length;
        updateImage(imageRight, imageContainerRight, currentIndexRight, sizeRight, filenameRight);
    });

    trashBtn.addEventListener('click', () => {
        if (images.length === 0) return;
        const image = images[currentIndexRight];
        const imagePath = currentDirectory ? `/images/${currentDirectory}/${image.name}` : `/images/${image.name}`;
        deletedImages.add(imagePath);
        updateImageViews();
    });

    restoreBtn.addEventListener('click', () => {
        if (images.length === 0) return;
        const image = images[currentIndexRight];
        const imagePath = currentDirectory ? `/images/${currentDirectory}/${image.name}` : `/images/${image.name}`;
        deletedImages.delete(imagePath);
        updateImageViews();
    });

    syncBtn.addEventListener('click', () => {
        if (images.length === 0) return;
        currentIndexLeft = currentIndexRight;
        updateImageViews();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight') {
            nextRightBtn.click();
        } else if (e.key === 'ArrowLeft') {
            prevRightBtn.click();
        } else if (e.key.toLowerCase() === 's') {
            syncBtn.click();
        } else if (e.key === ' ') {
            e.preventDefault(); // Prevent page scroll
            const image = images[currentIndexRight];
            const imagePath = currentDirectory ? `/images/${currentDirectory}/${image.name}` : `/images/${image.name}`;
            if (deletedImages.has(imagePath)) {
                restoreBtn.click();
            } else {
                trashBtn.click();
            }
        }
    });

    fetchDirectories();
    fetchImages(); // Fetch images from the root initially
});

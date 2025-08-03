
const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const port = 3000;

const imagesDirectory = path.join(__dirname, 'images');

// Serve static files from the "public" directory
app.use(express.static('public'));
app.use('/images', express.static(imagesDirectory));

// Function to recursively find all directories and count images
const getDirectoriesRecursive = (dirPath, allDirs = [], relativePath = '') => {
    const files = fs.readdirSync(dirPath, { withFileTypes: true });
    let imageCount = 0;

    files.forEach(file => {
        if (file.isDirectory()) {
            const newRelativePath = path.join(relativePath, file.name);
            allDirs.push(getDirectoriesRecursive(path.join(dirPath, file.name), [], newRelativePath));
        } else {
            const extension = path.extname(file.name).toLowerCase();
            if (['.jpg', '.jpeg', '.png', '.gif'].includes(extension)) {
                imageCount++;
            }
        }
    });

    // For the current directory, return its info
    return {
        path: relativePath,
        count: imageCount,
        subdirs: allDirs.flat()
    };
};

const flattenDirs = (dirInfo) => {
    let dirs = [{ path: dirInfo.path, count: dirInfo.count }];
    if (dirInfo.subdirs) {
        dirInfo.subdirs.forEach(subdir => {
            dirs = dirs.concat(flattenDirs(subdir));
        });
    }
    return dirs;
};

// API endpoint to get the list of subdirectories
app.get('/api/directories', (req, res) => {
    try {
        const dirInfo = getDirectoriesRecursive(imagesDirectory);
        const directories = flattenDirs(dirInfo);
        res.json(directories);
    } catch (err) {
        console.error("Could not list the directories.", err);
        return res.status(500).send('Internal Server Error');
    }
});


// API endpoint to get the list of images
app.get('/api/images', (req, res) => {
    const dir = req.query.dir || '';
    const currentDirectory = path.join(imagesDirectory, dir);

    // Basic security check to prevent directory traversal
    if (!currentDirectory.startsWith(imagesDirectory)) {
        return res.status(400).send('Invalid directory');
    }

    fs.readdir(currentDirectory, (err, files) => {
        if (err) {
            console.error("Could not list the directory.", err);
            return res.status(500).send('Internal Server Error');
        }

        const imageDetails = files
            .filter(file => {
                const extension = path.extname(file).toLowerCase();
                return ['.jpg', '.jpeg', '.png', '.gif'].includes(extension);
            })
            .map(file => {
                const filePath = path.join(currentDirectory, file);
                try {
                    const stats = fs.statSync(filePath);
                    return {
                        name: file,
                        size: stats.size
                    };
                } catch (statErr) {
                    console.error(`Could not get stats for file: ${filePath}`, statErr);
                    return null;
                }
            })
            .filter(Boolean); // Filter out nulls from failed statSync calls

        res.json(imageDetails);
    });
});

app.listen(port, () => {
    console.log(`Image viewer app listening at http://localhost:${port}`);
});

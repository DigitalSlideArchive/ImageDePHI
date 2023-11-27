export async function getDirectoryInfo(path?:string) {
    const selectedPath= path ? path : '';
    const response = await fetch('http://localhost:8000/directory/'+ selectedPath, {method: "GET", mode: 'cors'});

    return response.json()

}

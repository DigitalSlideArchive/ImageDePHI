## Development
For efficient front end developement in the project root run:

   ```bash
   export DEBUG=True
   hypercorn --reload imagedephi.gui:app
   ```

In a new terminal:

```bash
cd client/
yarn dev
```

**Note**
`imagedephi gui` will break and tests will fail in debug mode. Remember to reset variable when done with development.

```bash
export DEBUG=False
```

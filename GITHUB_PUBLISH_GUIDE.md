# Publish TrajectoryLab on GitHub (Windows)

The source folder contains a fresh local Git repository on branch `main` with
no project commit yet. This lets GitHub Desktop make the first commit using
your own Git identity.

1. Extract `TrajectoryLab.zip` to a permanent folder, for example
   `C:\Projects\TrajectoryLab`.
2. Install GitHub Desktop from <https://desktop.github.com/> and sign in.
3. In GitHub Desktop select **File → Add local repository** and choose the
   extracted `TrajectoryLab` folder.
4. Review the files shown as changes. The source repository intentionally does
   not contain the compiled Windows executable or previous Git history.
5. In the Summary field enter `Initial public preview 0.4.2`, then click
   **Commit to main**.
6. Select **Publish repository**. Set the name to `TrajectoryLab` and make sure
   **Keep this code private** is unchecked.
7. Publish to your personal account (or the intended organization).
8. Open the repository on GitHub and verify the README and files.
9. Create a GitHub Release tagged `v0.4.2-preview`; attach
   `TrajectoryLab_Windows_Builder_Package.zip` and `SHA256SUMS.txt` from the
   release assets prepared alongside this source package.

GitHub's documentation describes adding an existing local repository and
publishing it from GitHub Desktop:
<https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop>

## License

The project owner selected MIT for the original TrajectoryLab source code and
project-authored documentation. The license is in `LICENSE`; scope exclusions
are defined in `LICENSE_SCOPE.md`. Artwork and third-party dependencies are
not relicensed under MIT. Before publishing publicly, confirm redistribution
rights for the Recraft-generated logo and the cow photograph using
`ASSET_RIGHTS.md`.

## Binary release

The source repository does not track `build.exe`. The standalone Windows
bootstrapper is included in the full Builder package attached as a GitHub
Release asset. It is unsigned in this preview, so Windows SmartScreen may show
an unknown-publisher warning. Do not bypass a malware detection.

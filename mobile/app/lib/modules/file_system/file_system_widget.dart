import 'package:flutter/material.dart';
import 'file_system_module.dart';

class FileSystemWidget extends StatefulWidget {
  final FileSystemModule module;
  const FileSystemWidget({required this.module, super.key});

  @override
  State<FileSystemWidget> createState() => _FileSystemWidgetState();
}

class _FileSystemWidgetState extends State<FileSystemWidget> {
  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<bool>(
      valueListenable: widget.module.isNavigatingNotifier,
      builder: (context, isNavigating, child) {

        return Column(
          children: [
            // Breadcrumb Navigation
            _buildBreadcrumbs(),

            // File/Directory List
            Expanded(
              child: RefreshIndicator(
                onRefresh: () async {
                  await widget.module.fetchPath();
                },
                child: ValueListenableBuilder<List<FileSystemEntry>>(
                  valueListenable: widget.module.entriesNotifier,
                  builder: (context, entries, child) {
                    if (entries.isEmpty || isNavigating) {
                      return SingleChildScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        child: SizedBox(
                          height:
                              MediaQuery.of(context).size.height *
                              0.8, // Ensure enough space for pull-to-refresh
                          child: const Center(
                            child: Padding(
                              padding: EdgeInsets.all(16.0),
                              child: Text("No files found."),
                            ),
                          ),
                        ),
                      );
                    }

                    return ListView.builder(
                      physics: const AlwaysScrollableScrollPhysics(),
                      itemCount: entries.length,
                      itemBuilder: (context, index) {
                        final entry = entries[index];
                        return ListTile(
                          leading: Icon(
                            entry.isDirectory
                                ? Icons.folder
                                : Icons.insert_drive_file,
                          ),
                          title: Text(entry.name),
                          onTap: () {
                            if (entry.isDirectory) {
                              widget.module.navigateTo(entry.absPath);
                            } else {
                              widget.module.downloadFile(entry.absPath).then((
                                path,
                              ) {
                                if (path != null && mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('File saved to $path'),
                                    ),
                                  );
                                } else if (mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text(
                                        'Download failed. Check permissions.',
                                      ),
                                    ),
                                  );
                                }
                              });
                            }
                          },
                        );
                      },
                    );
                  },
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _breadCrumb(String segment, String navPath, int index, int total) {
    final isLast = index == total - 1;
    return GestureDetector(
      onTap: () => widget.module.navigateTo(navPath),
      child: Text(
        segment,
        style: TextStyle(
          color: isLast
          ? Theme.of(context).textTheme.bodyLarge?.color
          : Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
          decoration: TextDecoration.underline,
        ),
      ),
    );
  }

  // Breadcrumb Navigation
  Widget _buildBreadcrumbs() {
    return ValueListenableBuilder<String>(
      valueListenable: widget.module.currentPathNotifier,
      builder: (context, currentPath, child) {
        final segments = currentPath
            .split('/')
            .where((s) => s.isNotEmpty)
            .toList();
        List<Widget> breadcrumbs = [];

        // Add root breadcrumb ('~' or '/')
        final rootSegment = currentPath.startsWith('~') ? '~' : '/';
        breadcrumbs.add(_breadCrumb(rootSegment, rootSegment, 1, segments.length + 1));

        String cumulativePath = rootSegment;
        // Adjust starting index if root is '~'
        final startIndex =
            (rootSegment == '~' && segments.isNotEmpty && segments[0] == '~')
            ? 1
            : 0;

        for (int i = startIndex; i < segments.length; i++) {
          final segment = segments[i];
          // path.join logic for breadcrumbs
          if (cumulativePath == '/') {
            cumulativePath = '/$segment';
          } else {
            cumulativePath = '$cumulativePath/$segment';
          }

          // Add separator before adding the next segment
          breadcrumbs.add(
            const Padding(
              padding: EdgeInsetsGeometry.directional(start: 6.0, end: 6.0),
              child: Icon(Icons.chevron_right, size: 16, color: Colors.grey),
            ),
          );
          breadcrumbs.add(_breadCrumb(segment, cumulativePath, i + 1, segments.length + 1));
        }

        return Padding(
          padding: const EdgeInsets.all(8.0),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.start,
              children: breadcrumbs,
            ),
          ),
        );
      },
    );
  }
}

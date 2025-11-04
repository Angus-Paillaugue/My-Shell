import 'package:flutter/material.dart';
import 'package:vellum_shell_sync/modules/clipboard/clipboard_module.dart';

class ClipboardWidget extends StatefulWidget {
  final ClipboardModule module;
  const ClipboardWidget({required this.module, super.key});

  @override
  State<ClipboardWidget> createState() => _ClipboardWidgetState();
}

class _ClipboardWidgetState extends State<ClipboardWidget>
    with SingleTickerProviderStateMixin {
  late TabController tabController;

  @override
  void initState() {
    super.initState();
    tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TabBar(
          controller: tabController,
          tabs: const <Widget>[
            Tab(icon: Icon(Icons.laptop)),
            Tab(icon: Icon(Icons.phone_android)),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: tabController,
            children: <Widget>[remoteClipboardWidget(), localClipboardWidget()],
          ),
        ),
      ],
    );
  }

  Widget localClipboardWidget() {
    return Expanded(
      child: RefreshIndicator(
        onRefresh: () async {
          await widget.module.getLocalClipboard();
        },
        child: ValueListenableBuilder<String>(
          valueListenable: widget.module.localClipboard,
          builder: (context, entry, child) {
            if (entry == '') {
              return SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                child: SizedBox(
                  height: MediaQuery.of(context).size.height * 0.8,
                  child: const Center(
                    child: Padding(
                      padding: EdgeInsets.all(16.0),
                      child: Text("Clipboard is empty."),
                    ),
                  ),
                ),
              );
            }

            return ListTile(
              title: Text(entry),
              onTap: () {
                widget.module.sendClipboardContent(entry);
              },
            );
          },
        ),
      ),
    );
  }

  Widget remoteClipboardWidget() {
    return ValueListenableBuilder<bool>(
      valueListenable: widget.module.isFetchingRemote,
      builder: (context, isNavigating, child) {
        return Expanded(
          child: RefreshIndicator(
            onRefresh: () async {
              await widget.module.getRemoteClipboard();
            },
            child: ValueListenableBuilder<List<String>>(
              valueListenable: widget.module.remoteClipboard,
              builder: (context, entries, child) {
                if (entries.isEmpty || isNavigating) {
                  return SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    child: SizedBox(
                      height: MediaQuery.of(context).size.height * 0.8,
                      child: const Center(
                        child: Padding(
                          padding: EdgeInsets.all(16.0),
                          child: Text("Clipboard is empty."),
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
                      title: Text(entry),
                      onTap: () {
                        widget.module.copyToClipboard(entry);
                      },
                    );
                  },
                );
              },
            ),
          ),
        );
      },
    );
  }
}
